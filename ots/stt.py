import os
import platform


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
        else:
            from faster_whisper import WhisperModel

            self.model_obj = WhisperModel(model, device="cpu", compute_type=compute_type, cpu_threads=threads)

    @staticmethod
    def _resolve_backend(backend: str) -> str:
        if backend != "auto":
            return backend
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            try:
                import mlx_whisper  # noqa

                return "mlx-whisper"
            except Exception:
                pass
        return "faster-whisper"

    def transcribe_path(self, audio_path: str):
        if self.backend == "mlx-whisper":
            out = self.mlx_whisper.transcribe(audio_path, path_or_hf_repo=self.model)
            for seg in out.get("segments", []):
                text = (seg.get("text") or "").strip()
                if text:
                    yield text
        else:
            segments, _ = self.model_obj.transcribe(audio_path, beam_size=3, vad_filter=True)
            for seg in segments:
                text = seg.text.strip()
                if text:
                    yield text
