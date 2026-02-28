import queue
import time
import numpy as np
import sounddevice as sd
import soundfile as sf


def stream_mic_chunks(seconds_per_chunk: float = 4.0, samplerate: int = 16000):
    q = queue.Queue()

    def cb(indata, frames, time_info, status):
        q.put(indata.copy())

    with sd.InputStream(channels=1, samplerate=samplerate, callback=cb):
        buf, last = [], time.time()
        while True:
            chunk = q.get(timeout=1.0)
            buf.append(chunk)
            if time.time() - last >= seconds_per_chunk:
                wav = np.concatenate(buf, axis=0).flatten()
                path = "/tmp/ots_mic_chunk.wav"
                sf.write(path, wav, samplerate)
                yield path
                buf, last = [], time.time()
