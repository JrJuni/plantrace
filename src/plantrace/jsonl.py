import json
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_DIR = Path.home() / ".claude" / "plantrace" / "logs"


def event_log_path(log_dir: Path | None = None) -> Path:
    # Resolve default at call time so tests' monkeypatch on DEFAULT_LOG_DIR sticks.
    log_dir = log_dir or DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"events-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"


def append_event(payload: dict, log_dir: Path | None = None) -> Path:
    """Append a raw event line. Intentionally schema-loose — events.jsonl is the immutable raw trace; the SQLite events table (Phase 1B) is the curated projection."""
    log_dir = log_dir or DEFAULT_LOG_DIR
    path = event_log_path(log_dir)
    line = {"received_at": int(time.time()), **payload}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return path
