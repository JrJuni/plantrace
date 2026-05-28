"""Notion plan-artifact projector (Phase 1A: fail-soft, page-only).

`project_plan` creates a new nested page under the configured
`plan_artifact_parent_page_id` and stores the resulting Notion `page_id` on
the SQLite root node. It is intentionally fail-soft: any HTTP error, missing
token, or absent config returns `None` plus a JSONL skip/fail event — the
calling hook stays at exit 0 so SQLite-only success is still a success.

Phase 1B will add Node data source projection (one row per node). The 1A
page artifact is one-shot: full plan body as paragraph blocks + children as
a bulleted list, both chunked to respect Notion's 100-block-per-request limit
and 2000-char-per-rich-text limit.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any

from plantrace import jsonl


NOTION_API_BASE = "https://api.notion.com"
MAX_BLOCKS_PER_REQUEST = 100
MAX_TEXT_CONTENT_CHARS = 2000


def _chunk_text(text: str, limit: int = MAX_TEXT_CONTENT_CHARS) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def _paragraph_block(content: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"type": "text", "text": {"content": content}}
            ]
        },
    }


def _bullet_block(content: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [
                {"type": "text", "text": {"content": content}}
            ]
        },
    }


def _build_blocks(plan_text: str, child_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    # Plan body as one or more paragraph blocks, respecting 2000-char rich_text limit.
    for chunk in _chunk_text(plan_text):
        blocks.append(_paragraph_block(chunk))
    # Children summary as bulleted list.
    for rec in child_records:
        label = rec.get("plan_local_label") or ""
        title = rec.get("title") or ""
        internal_id = rec.get("internal_id") or ""
        content = f"[{label}] {title} ({internal_id})" if label else f"{title} ({internal_id})"
        # Defensive 2000-char clip on the line itself (children titles should be short).
        blocks.append(_bullet_block(content[:MAX_TEXT_CONTENT_CHARS]))
    return blocks


def _client():  # pragma: no cover - thin wrapper, exercised via tests with explicit transport.
    import httpx

    return httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0))


def _headers(token: str, api_version: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": api_version,
        "Content-Type": "application/json",
    }


def _update_root_notion_id(db_path, root_internal_id: str, notion_page_id: str) -> None:
    with sqlite3.connect(db_path) as raw:
        raw.execute(
            "UPDATE nodes SET notion_page_id = ? WHERE internal_id = ?",
            (notion_page_id, root_internal_id),
        )
        raw.commit()


def project_plan(
    root_record: dict[str, Any],
    child_records: list[dict[str, Any]],
    plan_text: str,
    config,
    *,
    client=None,
) -> str | None:
    """Project a freshly-persisted plan tree to Notion. Returns Notion page_id or None.

    Skip/fail cases all return None + a JSONL skip/fail event:
    - config.notion is None        → notion.skipped_no_config
    - NOTION_TOKEN env missing     → notion.skipped_no_token
    - HTTP error / network failure → notion.projection_failed

    The caller (hook) must treat None as non-fatal and exit 0.
    """
    if config.notion is None:
        jsonl.append_event(
            {"event": "notion.skipped_no_config", "root_id": root_record.get("internal_id")},
            log_dir=config.log_dir,
        )
        return None

    token = os.environ.get("NOTION_TOKEN")
    if not token:
        jsonl.append_event(
            {"event": "notion.skipped_no_token", "root_id": root_record.get("internal_id")},
            log_dir=config.log_dir,
        )
        return None

    parent_page_id = config.notion.plan_artifact_parent_page_id
    api_version = config.notion.api_version
    root_title = (root_record.get("title") or "Untitled plan")[:MAX_TEXT_CONTENT_CHARS]

    blocks = _build_blocks(plan_text, child_records)
    first_chunk = blocks[:MAX_BLOCKS_PER_REQUEST]
    rest_chunks: list[list[dict[str, Any]]] = []
    if len(blocks) > MAX_BLOCKS_PER_REQUEST:
        rest = blocks[MAX_BLOCKS_PER_REQUEST:]
        rest_chunks = [
            rest[i : i + MAX_BLOCKS_PER_REQUEST]
            for i in range(0, len(rest), MAX_BLOCKS_PER_REQUEST)
        ]

    create_payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "properties": {
            "title": {
                "title": [
                    {"type": "text", "text": {"content": root_title}}
                ]
            }
        },
        "children": first_chunk,
    }

    owns_client = client is None
    if owns_client:
        client = _client()

    try:
        try:
            resp = client.post(
                f"{NOTION_API_BASE}/v1/pages",
                headers=_headers(token, api_version),
                json=create_payload,
            )
        except Exception as exc:  # pragma: no cover - network classes vary
            jsonl.append_event(
                {
                    "event": "notion.projection_failed",
                    "root_id": root_record.get("internal_id"),
                    "stage": "create",
                    "error": f"{type(exc).__name__}: {str(exc)[:400]}",
                },
                log_dir=config.log_dir,
            )
            return None

        if resp.status_code not in (200, 201):
            jsonl.append_event(
                {
                    "event": "notion.projection_failed",
                    "root_id": root_record.get("internal_id"),
                    "stage": "create",
                    "status_code": resp.status_code,
                    "body": resp.text[:500],
                },
                log_dir=config.log_dir,
            )
            return None

        page_id = resp.json().get("id")
        if not page_id:
            jsonl.append_event(
                {
                    "event": "notion.projection_failed",
                    "root_id": root_record.get("internal_id"),
                    "stage": "create",
                    "error": "no page id in response",
                },
                log_dir=config.log_dir,
            )
            return None

        for chunk_idx, chunk in enumerate(rest_chunks, start=1):
            patch_resp = client.patch(
                f"{NOTION_API_BASE}/v1/blocks/{page_id}/children",
                headers=_headers(token, api_version),
                json={"children": chunk},
            )
            if patch_resp.status_code not in (200, 201):
                jsonl.append_event(
                    {
                        "event": "notion.projection_failed",
                        "root_id": root_record.get("internal_id"),
                        "stage": "append",
                        "chunk_index": chunk_idx,
                        "status_code": patch_resp.status_code,
                        "body": patch_resp.text[:500],
                    },
                    log_dir=config.log_dir,
                )
                # Page already exists; don't abort the JSONL stream — succeed partially.
                break

        _update_root_notion_id(config.sqlite_path, root_record["internal_id"], page_id)
        jsonl.append_event(
            {
                "event": "notion.projection_succeeded",
                "root_id": root_record.get("internal_id"),
                "notion_page_id": page_id,
                "blocks_total": len(blocks),
            },
            log_dir=config.log_dir,
        )
        return page_id
    finally:
        if owns_client:
            client.close()
