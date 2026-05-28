"""Phase 1A test isolation.

Goal: no test ever writes to the real user home. We do not require the real
`~/.claude/plantrace/` directory to be absent (E2E / dogfood may have created
one), but we must guarantee tests do not modify it as a side effect.

Mechanism (autouse, function-scope):
1. monkeypatch `pathlib.Path.home` to point at the per-test `tmp_path`.
2. monkeypatch `plantrace.db.DEFAULT_DB_PATH` and `plantrace.jsonl.DEFAULT_LOG_DIR`
   to tmp_path-rooted locations. This catches any caller that imported the
   default before the patch landed (defense-in-depth on top of P1.2's
   call-time lookup).
3. Capture the real home plantrace sentinel's mtime (if any) before yielding,
   and assert it is unchanged after the test. If the sentinel does not exist,
   require that the test did not create it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_REAL_HOME_PLANTRACE = Path.home() / ".claude" / "plantrace"


def _sentinel_mtime() -> float | None:
    try:
        return _REAL_HOME_PLANTRACE.stat().st_mtime
    except FileNotFoundError:
        return None


@pytest.fixture(autouse=True)
def tmp_home(tmp_path, monkeypatch):
    from plantrace import db as _db
    from plantrace import jsonl as _jsonl

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(_db, "DEFAULT_DB_PATH", tmp_path / ".claude" / "plantrace" / "state.db")
    monkeypatch.setattr(_jsonl, "DEFAULT_LOG_DIR", tmp_path / ".claude" / "plantrace" / "logs")

    before = _sentinel_mtime()
    yield tmp_path
    after = _sentinel_mtime()

    if before is None:
        assert after is None, (
            f"Test created real home plantrace dir at {_REAL_HOME_PLANTRACE}; "
            "fixture failed to isolate writes."
        )
    else:
        assert after == before, (
            f"Test mutated real home plantrace dir at {_REAL_HOME_PLANTRACE} "
            f"(mtime {before} -> {after}); fixture failed to isolate writes."
        )
