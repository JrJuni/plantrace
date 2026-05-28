import sqlite3
import time
from pathlib import Path

DEFAULT_DB_PATH = Path.home() / ".claude" / "plantrace" / "state.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    internal_id        TEXT PRIMARY KEY,
    parent_id          TEXT REFERENCES nodes(internal_id),
    title              TEXT NOT NULL,
    body               TEXT,
    plain_language     TEXT,
    status             TEXT NOT NULL CHECK (status IN ('planned','in_progress','completed')),
    source_type        TEXT,
    source_session     TEXT,
    source_plan_id     TEXT,
    source_ai          TEXT,
    source_timestamp   INTEGER,
    plan_local_label   TEXT,
    notion_page_id     TEXT,
    created_at         INTEGER NOT NULL,
    completed_at       INTEGER
);

CREATE INDEX IF NOT EXISTS idx_nodes_parent       ON nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_source_plan  ON nodes(source_plan_id);

CREATE TABLE IF NOT EXISTS node_tags (
    node_id    TEXT NOT NULL REFERENCES nodes(internal_id),
    tag_kind   TEXT NOT NULL CHECK (tag_kind IN ('lens','topic','custom')),
    tag_value  TEXT NOT NULL,
    PRIMARY KEY (node_id, tag_kind, tag_value)
);

CREATE TABLE IF NOT EXISTS relations (
    src_id         TEXT NOT NULL REFERENCES nodes(internal_id),
    dst_id         TEXT NOT NULL REFERENCES nodes(internal_id),
    relation_type  TEXT NOT NULL CHECK (relation_type IN ('ownership','influence','blocks','references')),
    created_at     INTEGER NOT NULL,
    PRIMARY KEY (src_id, dst_id, relation_type)
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SCHEMA_VERSION = "1"


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    # Resolve the default at call time, not import time, so monkeypatching
    # DEFAULT_DB_PATH in tests / hook config actually takes effect for callers
    # that pass no argument.
    db_path = db_path or DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or DEFAULT_DB_PATH
    conn = connect(db_path)
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT OR IGNORE INTO schema_meta(key, value) VALUES (?, ?)",
        ("schema_version", SCHEMA_VERSION),
    )
    conn.commit()
    return conn


def now_ts() -> int:
    return int(time.time())


def insert_node(
    conn: sqlite3.Connection,
    *,
    internal_id: str,
    title: str,
    parent_id: str | None,
    body: str | None,
    status: str,
    source_type: str | None,
    source_session: str | None,
    source_plan_id: str | None,
    source_ai: str | None,
    plan_local_label: str | None,
) -> None:
    conn.execute(
        """
        INSERT INTO nodes (
            internal_id, parent_id, title, body, status,
            source_type, source_session, source_plan_id, source_ai, source_timestamp,
            plan_local_label, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            internal_id, parent_id, title, body, status,
            source_type, source_session, source_plan_id, source_ai, now_ts(),
            plan_local_label, now_ts(),
        ),
    )
