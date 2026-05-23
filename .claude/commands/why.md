---
description: Trace a PlanNode's parent chain + source provenance (local SQLite, offline-capable).
allowed-tools: Bash
argument-hint: <node-id>
---

Run the `/why` query against the local plantrace SQLite database.

Execute:

```bash
plantrace-why "$ARGUMENTS"
```

If the command is not on PATH (package not yet installed), run from the project root:

```bash
python -m plantrace.slash.why "$ARGUMENTS"
```

Show the raw output verbatim — no interpretation needed.
