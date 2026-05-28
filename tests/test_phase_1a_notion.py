"""Phase 1A Notion projector acceptance tests (fail-soft, no real network).

Uses httpx.MockTransport so requests never leave the process.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import httpx
import pytest

from plantrace import config as config_mod
from plantrace import db
from plantrace.hooks import exit_plan_mode
from plantrace.notion import projector


REAL_PARENT_PAGE_ID = "36eb5106-a4a7-810a-test-parent-page"
API_VERSION = "2026-03-11"


@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "state.db"
    db.init_db(db_path).close()
    return db_path


@pytest.fixture
def cfg(tmp_path, tmp_db):
    return config_mod.Config(
        sqlite_path=tmp_db,
        log_dir=tmp_path / "logs",
        notion=config_mod.NotionConfig(
            plan_artifact_parent_page_id=REAL_PARENT_PAGE_ID,
            api_version=API_VERSION,
        ),
    )


@pytest.fixture
def cfg_no_notion(tmp_path, tmp_db):
    return config_mod.Config(
        sqlite_path=tmp_db,
        log_dir=tmp_path / "logs",
        notion=None,
    )


@pytest.fixture
def root_record(tmp_db):
    rid = "n_root1234"
    with db.connect(tmp_db) as conn:
        db.insert_node(
            conn,
            internal_id=rid,
            title="Bootstrap plan",
            parent_id=None,
            body="# Bootstrap\n\nbody text",
            status="planned",
            source_type="plan_mode",
            source_session="sess",
            source_plan_id="p_test",
            source_ai="claude-code",
            plan_local_label=None,
        )
        conn.commit()
    return {"internal_id": rid, "title": "Bootstrap plan", "plan_local_label": None}


@pytest.fixture
def child_records():
    return [
        {"internal_id": f"n_child{i:04d}", "title": f"Task {i}", "plan_local_label": f"B{i}"}
        for i in range(1, 4)
    ]


def _last_jsonl(log_dir: Path) -> list[dict]:
    files = sorted(log_dir.glob("events-*.jsonl"))
    if not files:
        return []
    return [json.loads(ln) for ln in files[-1].read_text(encoding="utf-8").splitlines()]


def _events(log_dir: Path) -> list[str]:
    return [e.get("event") for e in _last_jsonl(log_dir)]


# --- acceptance #1 + #2 + #3 + #4 (single happy-path call covers them all) ---

def test_create_page_headers_and_payload(cfg, root_record, child_records, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok-abc")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"id": "page-new-123"})

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        page_id = projector.project_plan(
            root_record, child_records, "# Plan body\n\nshort body", cfg, client=client
        )

    assert page_id == "page-new-123"

    # #1 headers
    assert captured["headers"]["authorization"] == "Bearer tok-abc"
    assert captured["headers"]["notion-version"] == API_VERSION
    assert captured["headers"]["content-type"] == "application/json"
    # #2 parent
    body = captured["body"]
    assert body["parent"]["type"] == "page_id"
    assert body["parent"]["page_id"] == REAL_PARENT_PAGE_ID
    # #3 title
    assert body["properties"]["title"]["title"][0]["text"]["content"] == "Bootstrap plan"
    # #4 children blocks
    block_types = [b["type"] for b in body["children"]]
    assert "paragraph" in block_types
    assert block_types.count("bulleted_list_item") == 3


# --- acceptance #5 ---

def test_success_updates_root_notion_id_and_logs(cfg, root_record, child_records, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok-abc")
    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"id": "page-xyz"})
    )
    with httpx.Client(transport=transport) as client:
        projector.project_plan(
            root_record, child_records, "body", cfg, client=client
        )

    with sqlite3.connect(cfg.sqlite_path) as raw:
        raw.row_factory = sqlite3.Row
        row = raw.execute(
            "SELECT notion_page_id FROM nodes WHERE internal_id = ?",
            (root_record["internal_id"],),
        ).fetchone()
        assert row["notion_page_id"] == "page-xyz"

    assert "notion.projection_succeeded" in _events(cfg.log_dir)


# --- acceptance #6 ---

def test_5xx_is_failsoft(cfg, root_record, child_records, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok-abc")
    transport = httpx.MockTransport(
        lambda req: httpx.Response(503, text="upstream blew up")
    )
    with httpx.Client(transport=transport) as client:
        result = projector.project_plan(
            root_record, child_records, "body", cfg, client=client
        )
    assert result is None
    failed = [e for e in _last_jsonl(cfg.log_dir) if e.get("event") == "notion.projection_failed"]
    assert failed and failed[-1]["status_code"] == 503


# --- acceptance #7 ---

def test_no_token_skips_without_request(cfg, root_record, child_records, monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    call_count = {"n": 0}

    def handler(req):
        call_count["n"] += 1
        return httpx.Response(500)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = projector.project_plan(
            root_record, child_records, "body", cfg, client=client
        )
    assert result is None
    assert call_count["n"] == 0
    assert "notion.skipped_no_token" in _events(cfg.log_dir)


# --- acceptance #8 ---

def test_no_config_skips(cfg_no_notion, root_record, child_records, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok-abc")
    result = projector.project_plan(
        root_record, child_records, "body", cfg_no_notion
    )
    assert result is None
    assert "notion.skipped_no_config" in _events(cfg_no_notion.log_dir)


# --- acceptance #9 ---

def test_chunks_when_over_100_blocks(cfg, root_record, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok-abc")
    many_children = [
        {"internal_id": f"n_{i:04d}", "title": f"T{i}", "plan_local_label": f"B{i}"}
        for i in range(1, 251)  # 250 children → 250 bullet blocks + paragraph(s) > 100
    ]
    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        calls.append({"method": request.method, "url": str(request.url), "body": body})
        if request.method == "POST":
            return httpx.Response(200, json={"id": "page-big"})
        return httpx.Response(200, json={"results": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        page_id = projector.project_plan(
            root_record, many_children, "body", cfg, client=client
        )
    assert page_id == "page-big"
    # First call POST /v1/pages with <=100 blocks
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"].endswith("/v1/pages")
    assert len(calls[0]["body"]["children"]) <= 100
    # Subsequent calls PATCH /v1/blocks/{id}/children
    follow_ups = calls[1:]
    assert follow_ups, "expected at least one PATCH append"
    for c in follow_ups:
        assert c["method"] == "PATCH"
        assert "/v1/blocks/page-big/children" in c["url"]
        assert len(c["body"]["children"]) <= 100


# --- acceptance #10 ---

def test_long_body_splits_into_multiple_paragraph_blocks(cfg, root_record, monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok-abc")
    long_text = "x" * 5500  # 5500 chars → 3 paragraph chunks at 2000 each
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"id": "page-long"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        projector.project_plan(root_record, [], long_text, cfg, client=client)

    paragraph_count = sum(1 for b in captured["body"]["children"] if b["type"] == "paragraph")
    assert paragraph_count == 3
    for b in captured["body"]["children"]:
        if b["type"] == "paragraph":
            assert len(b["paragraph"]["rich_text"][0]["text"]["content"]) <= 2000


# --- hook integration: exit 0 + skipped_no_config when config.notion is None ---

def test_hook_main_with_no_notion_config_still_persists(tmp_path, monkeypatch):
    """End-to-end via the hook entry — config has no notion, hook still exits 0 and projects nothing."""
    # The autouse conftest fixture already isolates home; override CLAUDE_PROJECT_DIR to a clean dir.
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    payload = {
        "tool_name": "ExitPlanMode",
        "tool_response": {"plan": "# Demo\n- [ ] one\n"},
    }
    payload_bytes = json.dumps(payload).encode("utf-8")

    class _Buf:
        def read(self):
            return payload_bytes

    class _Stdin:
        buffer = _Buf()

        def read(self):  # not used by main(), kept for safety
            return payload_bytes.decode("utf-8")

    monkeypatch.setattr("sys.stdin", _Stdin())
    rc = exit_plan_mode.main()
    assert rc == 0
