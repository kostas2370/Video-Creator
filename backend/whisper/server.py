import io
import json
import logging
import os
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)
inference_lock = Lock()
MAX_AUDIO_BYTES = 32 * 1024 * 1024


@lru_cache(maxsize=1)
def get_model():
    return WhisperModel(
        os.getenv("WHISPER_MODEL") or "small",
        device="cpu",
        compute_type="int8",
        cpu_threads=int(os.getenv("WHISPER_CPU_THREADS") or 4),
        download_root=os.getenv("HF_HOME"),
    )


def transcribe(audio):
    with inference_lock:
        segments, info = get_model().transcribe(
            io.BytesIO(audio),
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        words = [
            {"word": word.word, "start": word.start, "end": word.end}
            for segment in segments
            for word in segment.words or []
        ]
    return {"words": words, "language": info.language}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/health":
            self.reply(404, {"error": "Not found"})
            return
        self.reply(
            200, {"status": "ok", "model_loaded": bool(get_model.cache_info().currsize)}
        )

    def do_POST(self):
        if self.path != "/transcribe":
            self.reply(404, {"error": "Not found"})
            return
        try:
            size = int(self.headers.get("Content-Length", 0))
        except ValueError:
            self.reply(400, {"error": "Invalid content length"})
            return
        if not 0 < size <= MAX_AUDIO_BYTES:
            self.reply(413, {"error": "Audio must be between 1 byte and 32 MB"})
            return
        self.connection.settimeout(60)
        try:
            audio = self.rfile.read(size)
            if len(audio) != size:
                self.reply(400, {"error": "Incomplete audio"})
                return
            result = transcribe(audio)
        except Exception:
            logger.exception("Local transcription failed")
            self.reply(503, {"error": "Local transcription failed"})
            return
        self.reply(200, result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ThreadingHTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
