"""Phase 1A end-to-end tests (local-only, no Notion).

Run with: pytest tests/test_phase_1a.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from plantrace import db, ids
from plantrace.hooks import exit_plan_mode
from plantrace.slash import why


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "state.db"
    monkeypatch.setattr(db, "DEFAULT_DB_PATH", db_path)
    return db_path


@pytest.fixture
def tmp_log_dir(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    from plantrace import jsonl as jsonl_mod
    monkeypatch.setattr(jsonl_mod, "DEFAULT_LOG_DIR", log_dir)
    return log_dir


def test_schema_creates_three_tables(tmp_db):
    conn = db.init_db(tmp_db)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"nodes", "node_tags", "relations"} <= tables
    assert conn.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'"
    ).fetchone()[0] == db.SCHEMA_VERSION


def test_id_generation_is_unique_and_prefixed():
    a, b = ids.new_node_id(), ids.new_node_id()
    assert a != b
    assert a.startswith("n_") and len(a) == len("n_") + 8


def test_extract_plan_text_from_tool_response():
    payload = {"tool_response": {"plan": "# Hello\n- [ ] task one\n"}}
    assert exit_plan_mode.extract_plan_text(payload) == "# Hello\n- [ ] task one\n"


def test_extract_plan_text_from_tool_input_fallback():
    payload = {"tool_input": {"plan": "fallback"}}
    assert exit_plan_mode.extract_plan_text(payload) == "fallback"


def test_extract_plan_text_from_file_path(tmp_path):
    f = tmp_path / "plan.md"
    f.write_text("from file", encoding="utf-8")
    payload = {"tool_response": {"plan_file_path": str(f)}}
    assert exit_plan_mode.extract_plan_text(payload) == "from file"


def test_extract_plan_text_returns_none_when_missing():
    assert exit_plan_mode.extract_plan_text({}) is None


def test_split_children_prefers_checklist():
    text = "# Master\nIntro line.\n- [ ] Alpha\n- [x] Beta\n1. ignored when checklist exists\n"
    root, children = exit_plan_mode.split_children(text)
    assert root == "Master"
    assert children == ["Alpha", "Beta"]


def test_split_children_falls_back_to_numbered():
    text = "Top\n1. First\n2. Second\n"
    root, children = exit_plan_mode.split_children(text)
    assert root == "Top"
    assert children == ["First", "Second"]


def test_persist_plan_creates_root_plus_children(tmp_db, tmp_log_dir):
    payload = {
        "session_id": "sess-test",
        "tool_response": {
            "plan": "# Bootstrap\n- [ ] Capture ExitPlanMode\n- [ ] Write /why\n"
        },
    }
    text = exit_plan_mode.extract_plan_text(payload)
    root_id, child_ids = exit_plan_mode.persist_plan(payload, text)

    assert len(child_ids) == 2

    with sqlite3.connect(tmp_db) as raw:
        raw.row_factory = sqlite3.Row
        root = raw.execute(
            "SELECT * FROM nodes WHERE internal_id = ?", (root_id,)
        ).fetchone()
        assert root["title"] == "Bootstrap"
        assert root["parent_id"] is None
        assert root["body"].startswith("# Bootstrap")
        assert root["status"] == "planned"
        assert root["source_type"] == "plan_mode"

        children = raw.execute(
            "SELECT * FROM nodes WHERE parent_id = ? ORDER BY plan_local_label",
            (root_id,),
        ).fetchall()
        assert [c["title"] for c in children] == ["Capture ExitPlanMode", "Write /why"]
        assert [c["plan_local_label"] for c in children] == ["B1", "B2"]
        assert all(c["source_plan_id"] == root["source_plan_id"] for c in children)


def test_why_walks_up_to_root(tmp_db, tmp_log_dir):
    payload = {
        "tool_response": {"plan": "# Root\n- [ ] Child task\n"},
    }
    text = exit_plan_mode.extract_plan_text(payload)
    root_id, child_ids = exit_plan_mode.persist_plan(payload, text)

    with db.init_db(tmp_db) as conn:
        chain = why.walk_up(conn, child_ids[0])

    assert [r["internal_id"] for r in chain] == [child_ids[0], root_id]
    rendered = why.render(chain)
    assert "Child task" in rendered
    assert "Root" in rendered


def test_main_appends_jsonl_event_log(tmp_db, tmp_log_dir, monkeypatch):
    payload = {
        "tool_name": "ExitPlanMode",
        "tool_response": {"plan": "# X\n- [ ] one\n"},
    }
    monkeypatch.setattr("sys.stdin", _stdin(json.dumps(payload)))
    rc = exit_plan_mode.main()
    assert rc == 0

    log_files = list(tmp_log_dir.glob("events-*.jsonl"))
    assert log_files, "expected at least one events-*.jsonl"
    lines = log_files[0].read_text(encoding="utf-8").strip().splitlines()
    events = [json.loads(ln)["event"] for ln in lines]
    assert "exit_plan_mode.received" in events
    assert "exit_plan_mode.persisted" in events


class _stdin:
    def __init__(self, text: str):
        self._text = text

    def read(self) -> str:
        return self._text
