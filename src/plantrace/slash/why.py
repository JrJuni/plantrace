"""/why <node-id> — walk parent chain + show source provenance.

Pure local SQLite. Works offline.
"""

from __future__ import annotations

import argparse
import sys

from plantrace import db


def fetch_node(conn, node_id: str):
    return conn.execute(
        "SELECT * FROM nodes WHERE internal_id = ?",
        (node_id,),
    ).fetchone()


def walk_up(conn, node_id: str):
    chain = []
    current = node_id
    while current:
        row = fetch_node(conn, current)
        if row is None:
            break
        chain.append(row)
        current = row["parent_id"]
    return chain


def render(chain) -> str:
    if not chain:
        return "No such node."
    leaf = chain[0]
    lines = []
    lines.append(f"why {leaf['internal_id']}  ({leaf['status']})")
    lines.append(f"  title: {leaf['title']}")
    if leaf["plan_local_label"]:
        lines.append(f"  plan-local label: {leaf['plan_local_label']}")
    if leaf["source_plan_id"]:
        lines.append(
            f"  source: {leaf['source_type'] or '?'} "
            f"({leaf['source_ai'] or '?'}, plan {leaf['source_plan_id']})"
        )
    if len(chain) > 1:
        lines.append("")
        lines.append("ancestors:")
        for i, row in enumerate(chain[1:], start=1):
            indent = "  " * i
            lines.append(f"{indent}└─ {row['title']}  [{row['internal_id']}]")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(prog="plantrace-why")
    parser.add_argument("node_id", help="Internal id of the node to trace")
    args = parser.parse_args()

    with db.init_db() as conn:
        chain = walk_up(conn, args.node_id)
        sys.stdout.write(render(chain) + "\n")
    return 0 if chain else 1


if __name__ == "__main__":
    sys.exit(main())
