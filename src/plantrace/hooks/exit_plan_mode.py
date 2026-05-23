"""ExitPlanMode PostToolUse hook entry point.

Reads PostToolUse JSON from stdin, persists the plan as a PlanNode tree
(root master + 1+ children parsed from the plan body), and appends the raw
payload to the JSONL event log.

Phase 1A scope:
- Local SQLite write only (no Notion projection yet).
- Children parsing is heuristic: top-level markdown checklist items (`- [ ]` /
  `- [x]`) or numbered list items become children. If neither pattern matches,
  the plan stores as a single root with no children — `/why` still works.

The exact ExitPlanMode payload shape is the subject of the Phase 0 spike. This
file targets the Round 3 external AI claim (`tool_response.plan` carries the
plan markdown; `tool_response.plan_file_path` may also be present). If the
spike contradicts this, update `extract_plan_text` accordingly and rerun.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from plantrace import db, ids, jsonl


CHECKLIST_RE = re.compile(r"^\s*-\s*\[[ xX]\]\s+(.+?)\s*$", re.MULTILINE)
NUMBERED_RE = re.compile(r"^\s*\d+\.\s+(.+?)\s*$", re.MULTILINE)


def extract_plan_text(payload: dict) -> str | None:
    """Resolve plan markdown from the PostToolUse payload.

    Tries (in order):
    1. tool_response.plan        — Round 3 external AI claim
    2. tool_input.plan           — fallback if shape differs
    3. read from tool_response.plan_file_path
    Returns None if nothing resolvable — caller logs and exits cleanly.
    """
    response = payload.get("tool_response") or {}
    if isinstance(response, dict):
        if isinstance(response.get("plan"), str) and response["plan"].strip():
            return response["plan"]
        path = response.get("plan_file_path") or response.get("planFilePath")
        if isinstance(path, str) and Path(path).is_file():
            return Path(path).read_text(encoding="utf-8")
    tool_input = payload.get("tool_input") or {}
    if isinstance(tool_input, dict):
        if isinstance(tool_input.get("plan"), str) and tool_input["plan"].strip():
            return tool_input["plan"]
    return None


def split_children(plan_text: str) -> tuple[str, list[str]]:
    """Return (root_title, child_titles).

    Root title = first non-empty line (strip leading '#'). Children = checklist
    items if any, else numbered list items. The full plan body is stored on the
    root regardless.
    """
    lines = [ln for ln in plan_text.splitlines() if ln.strip()]
    root_title = "Untitled plan"
    if lines:
        root_title = lines[0].lstrip("#").strip() or "Untitled plan"

    children = [m.strip() for m in CHECKLIST_RE.findall(plan_text)]
    if not children:
        children = [m.strip() for m in NUMBERED_RE.findall(plan_text)]
    return root_title, children


def persist_plan(payload: dict, plan_text: str) -> tuple[str, list[str]]:
    """Insert root + children into SQLite. Returns (root_id, child_ids)."""
    root_title, child_titles = split_children(plan_text)
    plan_id = ids.new_plan_id()
    session = (payload.get("session_id") or "")[:64] or None

    root_id = ids.new_node_id()
    with db.init_db() as conn:
        db.insert_node(
            conn,
            internal_id=root_id,
            title=root_title,
            parent_id=None,
            body=plan_text,
            status="planned",
            source_type="plan_mode",
            source_session=session,
            source_plan_id=plan_id,
            source_ai="claude-code",
            plan_local_label=None,
        )
        child_ids: list[str] = []
        for idx, title in enumerate(child_titles, start=1):
            child_id = ids.new_node_id()
            db.insert_node(
                conn,
                internal_id=child_id,
                title=title,
                parent_id=root_id,
                body=None,
                status="planned",
                source_type="plan_mode",
                source_session=session,
                source_plan_id=plan_id,
                source_ai="claude-code",
                plan_local_label=f"B{idx}",
            )
            child_ids.append(child_id)
        conn.commit()
    return root_id, child_ids


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        jsonl.append_event({"event": "exit_plan_mode.parse_error", "raw": raw})
        return 0

    jsonl.append_event({"event": "exit_plan_mode.received", "payload": payload})

    plan_text = extract_plan_text(payload)
    if not plan_text:
        jsonl.append_event({"event": "exit_plan_mode.no_plan_text"})
        return 0

    root_id, child_ids = persist_plan(payload, plan_text)
    jsonl.append_event({
        "event": "exit_plan_mode.persisted",
        "root_id": root_id,
        "child_count": len(child_ids),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
