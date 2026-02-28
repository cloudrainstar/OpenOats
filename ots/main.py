#!/usr/bin/env python3
import argparse
from dataclasses import asdict
from datetime import datetime, timezone

from ots.kb import KB
from ots.logic import suggest
from ots.models import Utterance
from ots.storage import SessionStore
from ots.stt import Transcriber


def run_file(audio: str, stt: Transcriber):
    for text in stt.transcribe_path(audio):
        yield Utterance(ts=datetime.now(timezone.utc).isoformat(), speaker="OTHER", text=text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--kb")
    ap.add_argument("--backend", default="auto", choices=["auto", "faster-whisper", "mlx-whisper"])
    ap.add_argument("--model", default="small")
    ap.add_argument("--compute-type", default="int8")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    store = SessionStore(enabled=not args.no_save)
    kb = KB(args.kb)
    stt = Transcriber(args.backend, args.model, args.compute_type, args.threads)

    print("On The Spot running…")
    for turn in run_file(args.audio, stt):
        ctx = kb.search(turn.text)
        points = suggest(turn.text, ctx)
        print(f"\n[{turn.speaker}] {turn.text}")
        for p in points:
            print(f" - {p}")
        store.append({"type": "turn", **asdict(turn), "context": ctx, "suggestions": points})


if __name__ == "__main__":
    main()
