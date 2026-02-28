#!/usr/bin/env python3
import argparse
import json
import os
import platform
import queue
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Utterance:
    ts: str
    speaker: str
    text: str


class SessionStore:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.path = None
        if enabled:
            Path("data/sessions").mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            self.path = Path(f"data/sessions/{stamp}.jsonl")

    def append(self, obj: dict):
        if not self.enabled or not self.path:
            return
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


class KB:
    def __init__(self, kb_dir: str | None):
        self.docs = []
        self.vectorizer = None
        self.matrix = None
        if kb_dir:
            p = Path(kb_dir)
            if p.exists():
                for fp in p.rglob("*"):
                    if fp.is_file() and fp.suffix.lower() in {".md", ".txt"}:
                        text = fp.read_text(encoding="utf-8", errors="ignore").strip()
                        if text:
                            self.docs.append((str(fp), text))
        if self.docs:
            self.vectorizer = TfidfVectorizer(stop_words="english", max_features=12000)
            self.matrix = self.vectorizer.fit_transform([d[1] for d in self.docs])

    def search(self, query: str, k: int = 3):
        if not self.docs or not self.vectorizer or self.matrix is None:
            return []
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix)[0]
        idxs = np.argsort(-sims)[:k]
        out = []
        for i in idxs:
            if sims[i] <= 0:
                continue
            path, txt = self.docs[i]
            out.append({"path": path, "score": float(sims[i]), "snippet": txt[:300].replace("\n", " ")})
        return out


def suggest(turn: Utterance, ctx: list[dict]) -> list[str]:
    points = []
    if ctx:
        points.append(f"Reference: {Path(ctx[0]['path']).name} (relevance {ctx[0]['score']:.2f})")
    q = turn.text.lower()
    if "pricing" in q or "cost" in q:
        points.append("Ask for budget range and buying timeline before proposing scope.")
    if "next" in q or "plan" in q:
        points.append("Offer 2 concrete next steps with owners and dates.")
    if "problem" in q or "issue" in q:
        points.append("Mirror the problem in one sentence, then propose a testable fix.")
    if not points:
        points.append("Reply with: clarify goal → confirm constraints → offer one concrete move.")
    return points[:3]


class Transcriber:
    def __init__(self, backend: str, model: str, compute_type: str, threads: int):
        self.backend = self._resolve_backend(backend)
        self.model = model
        self.compute_type = compute_type
        self.threads = threads
        os.environ["OMP_NUM_THREADS"] = str(threads)
        os.environ["MKL_NUM_THREADS"] = str(threads)

        if self.backend == "mlx-whisper":
            import mlx_whisper

            self.mlx_whisper = mlx_whisper
            print("STT backend: mlx-whisper (Apple Silicon optimized)")
        else:
            from faster_whisper import WhisperModel

            self.model_obj = WhisperModel(model, device="cpu", compute_type=compute_type, cpu_threads=threads)
            print(f"STT backend: faster-whisper ({compute_type}, {threads} threads)")

    @staticmethod
    def _resolve_backend(backend: str) -> str:
        if backend != "auto":
            return backend
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            try:
                import mlx_whisper  # noqa: F401

                return "mlx-whisper"
            except Exception:
                return "faster-whisper"
        return "faster-whisper"

    def transcribe_path(self, audio_path: str):
        if self.backend == "mlx-whisper":
            out = self.mlx_whisper.transcribe(audio_path, path_or_hf_repo=self.model)
            for seg in out.get("segments", []):
                txt = (seg.get("text") or "").strip()
                if txt:
                    yield txt
        else:
            segments, _ = self.model_obj.transcribe(audio_path, beam_size=3, vad_filter=True)
            for seg in segments:
                txt = seg.text.strip()
                if txt:
                    yield txt


def transcribe_file(audio_path: str, stt: Transcriber):
    for text in stt.transcribe_path(audio_path):
        yield Utterance(ts=datetime.now(timezone.utc).isoformat(), speaker="OTHER", text=text)


def transcribe_mic(stt: Transcriber):
    import sounddevice as sd
    import soundfile as sf

    q = queue.Queue()
    sr = 16000

    def cb(indata, frames, time_info, status):
        q.put(indata.copy())

    with sd.InputStream(channels=1, samplerate=sr, callback=cb):
        buf, last = [], time.time()
        while True:
            try:
                chunk = q.get(timeout=1.0)
                buf.append(chunk)
                if time.time() - last >= 4.0:
                    wav = np.concatenate(buf, axis=0).flatten()
                    tmp = "/tmp/ots_chunk.wav"
                    sf.write(tmp, wav, sr)
                    for txt in stt.transcribe_path(tmp):
                        yield Utterance(ts=datetime.now(timezone.utc).isoformat(), speaker="YOU", text=txt)
                    buf, last = [], time.time()
            except queue.Empty:
                continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", help="Path to meeting audio file (mp3/wav/m4a)")
    ap.add_argument("--kb", help="Knowledge base folder (.md/.txt files)")
    ap.add_argument("--model", default="small", help="Whisper model (faster-whisper) or mlx model name")
    ap.add_argument("--backend", default="auto", choices=["auto", "faster-whisper", "mlx-whisper"])
    ap.add_argument("--compute-type", default="int8", choices=["int8", "int8_float16", "float16", "float32"])
    ap.add_argument("--threads", type=int, default=max(2, (os.cpu_count() or 4) - 1))
    ap.add_argument("--no-save", action="store_true", help="Disable transcript saving")
    args = ap.parse_args()

    store = SessionStore(enabled=not args.no_save)
    kb = KB(args.kb)
    stt = Transcriber(args.backend, args.model, args.compute_type, args.threads)

    print("On The Spot MVP running...")
    print("Saving:", "ON" if store.enabled else "OFF")

    source = transcribe_file(args.audio, stt) if args.audio else transcribe_mic(stt)

    for turn in source:
        ctx = kb.search(turn.text, k=3)
        points = suggest(turn, ctx)

        print(f"\n[{turn.speaker}] {turn.text}")
        if ctx:
            print("  Context:")
            for c in ctx[:2]:
                print(f"   - {Path(c['path']).name}: {c['snippet'][:120]}...")
        print("  Suggested talking points:")
        for p in points:
            print(f"   - {p}")

        store.append({"type": "turn", **asdict(turn), "context": ctx, "suggestions": points})


if __name__ == "__main__":
    main()
