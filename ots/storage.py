import json
from datetime import datetime, timezone
from pathlib import Path


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
