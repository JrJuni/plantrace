"""Project-scoped configuration loader.

Reads `<project_dir>/.claude/plantrace.json` if present, otherwise returns a
defaults-only Config. Notion projection is only activated when the config has
a real `plan_artifact_parent_page_id` (i.e., not a `REPLACE_*` placeholder)
and a real `api_version`. The `NOTION_TOKEN` env var is checked separately at
projection call time, not here — token absence is a runtime skip, not a
config-load failure.

Phase 1A scope: the projector only reads `plan_artifact_parent_page_id` and
`api_version`. Other Notion fields (`workspace_id`, `node_data_source_id`)
may stay as placeholders until Phase 1B introduces the Node data source.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


_PLACEHOLDER_PREFIX = "REPLACE_"


@dataclass(frozen=True)
class NotionConfig:
    plan_artifact_parent_page_id: str
    api_version: str
    workspace_id: str | None = None
    node_data_source_id: str | None = None


@dataclass(frozen=True)
class Config:
    sqlite_path: Path
    log_dir: Path
    notion: NotionConfig | None


def _expand(path_str: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def _is_placeholder(value: str | None) -> bool:
    return not value or value.startswith(_PLACEHOLDER_PREFIX)


def _default_sqlite_path() -> Path:
    return Path.home() / ".claude" / "plantrace" / "state.db"


def _default_log_dir() -> Path:
    return Path.home() / ".claude" / "plantrace" / "logs"


def _resolve_project_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path.cwd()


def _build_notion(raw: dict) -> NotionConfig | None:
    parent_id = raw.get("plan_artifact_parent_page_id")
    if _is_placeholder(parent_id):
        print(
            "[plantrace] notion projection disabled: plan_artifact_parent_page_id is placeholder",
            file=sys.stderr,
        )
        return None
    api_version = raw.get("api_version") or "2026-03-11"
    return NotionConfig(
        plan_artifact_parent_page_id=parent_id,
        api_version=api_version,
        workspace_id=raw.get("workspace_id"),
        node_data_source_id=raw.get("node_data_source_id"),
    )


def load_config(project_dir: Path | None = None) -> Config:
    project_dir = _resolve_project_dir(project_dir)
    config_path = project_dir / ".claude" / "plantrace.json"

    sqlite_path = _default_sqlite_path()
    log_dir = _default_log_dir()
    notion: NotionConfig | None = None

    if config_path.is_file():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        local = data.get("local") or {}
        if "sqlite_path" in local:
            sqlite_path = _expand(local["sqlite_path"])
        if "log_dir" in local:
            log_dir = _expand(local["log_dir"])
        if isinstance(data.get("notion"), dict):
            notion = _build_notion(data["notion"])

    return Config(sqlite_path=sqlite_path, log_dir=log_dir, notion=notion)
