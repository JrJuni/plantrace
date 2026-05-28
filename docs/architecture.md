# Architecture

> Phase 1A snapshot. The tool deliberately starts as **hook → SQLite → optional Notion projection** with no MCP server, no LangGraph, no classifier. Layers are added in later phases against the criteria in `roadmap.md`; this doc evolves with them.

## Surfaces (Phase 1A)

There is one surface — a Claude Code `PostToolUse` hook for `ExitPlanMode` — feeding one orchestration core (the persistence pipeline). Notion is a downstream projection, not a surface.

```
        ┌────────────────────────────────────────────────┐
        │  Claude Code session                           │   (primary)
        │     ExitPlanMode tool call                     │
        └─────────────────────┬──────────────────────────┘
                              │  PostToolUse JSON over stdin
                              ▼
        ┌────────────────────────────────────────────────┐
        │  src/plantrace/hooks/exit_plan_mode.py         │
        │     extract_plan_text → split_children →       │
        │     persist_plan → notion_projector            │
        └─────────────────────┬──────────────────────────┘
                              │
              ┌───────────────┼────────────────────────────┐
              ▼               ▼                            ▼
        SQLite (SSOT)   JSONL raw event log         Notion (projection)
        ~/.claude/      ~/.claude/plantrace/        page-only artifact,
        plantrace/      logs/events-{date}.jsonl    fail-soft
        state.db
```

The hook is the day-to-day driver (Phase 1A's "vertical slice"). Local SQLite is the durable source of truth — `decisions.md` row 8. Notion is a one-shot projection of the Plan artifact page; the Node data_source is Phase 1B, not yet wired. The JSONL stream is the immutable raw trace; `decisions.md` row 17 commits to keeping it from Phase 1A onward.

`/why` (Phase 1A) reads SQLite directly, no network. `/impact` / `/orphans` / `/sync` / `/coverage` / `/stale` are Phase 1B (see `roadmap.md`).

## Configuration flow

- `.claude/plantrace.json` in the project root → validated against `schemas/plantrace.schema.json` (v1). Example: `examples/plantrace.json`.
- `src/plantrace/config.py::load_config()` reads it lazily, returns a frozen `Config(sqlite_path, log_dir, notion: NotionConfig | None)`.
- **Placeholder detection**: any field starting with `REPLACE_` collapses `notion` to `None`. The hook then logs `notion.skipped_no_config` and stays at exit 0 — SQLite-only success is still a success. Decisions: `_PLACEHOLDER_PREFIX` in `config.py`.
- **`NOTION_TOKEN` env var** is checked at projection call time (`notion/projector.py`), not config load — token absence is a runtime skip, never a config-load failure.
- **`CLAUDE_PROJECT_DIR`** env var resolves project root when set (Claude Code provides it); falls back to `Path.cwd()`.
- API version is pinned to `2026-03-11` (`decisions.md` row 10). Bump only via the Revisit trigger.

## SQLite schema (Phase 1A)

`src/plantrace/db.py::_SCHEMA` defines four tables. `init_db()` is idempotent (`CREATE TABLE IF NOT EXISTS`) and seeds `schema_meta.schema_version = "1"`.

| Table | Purpose | Notes |
|---|---|---|
| `nodes` | PlanNode rows (root + children) | `internal_id` PK, `parent_id` FK self-reference, `status` CHECK (`planned`/`in_progress`/`completed`), `notion_page_id` is populated only after a successful projection. Indices on `parent_id` and `source_plan_id`. |
| `node_tags` | Lens / topic / custom tags | `(node_id, tag_kind, tag_value)` composite PK. `tag_kind` CHECK whitelist: `lens` / `topic` / `custom`. Not yet populated in Phase 1A (lens system activates in Phase 1B). |
| `relations` | Cross-cutting graph (4 kinds) | `(src_id, dst_id, relation_type)` composite PK. `relation_type` CHECK: `ownership` / `influence` / `blocks` / `references` (`decisions.md` row 5). Phase 1A only writes parent_id; `/impact` is Phase 1B. |
| `schema_meta` | Single-row registry | `schema_version` key drives future migrations. No Alembic yet — Phase 1A is a `CREATE TABLE IF NOT EXISTS` regime; migration scaffolding is part of the Phase 1B work that introduces the `events` table. |

`PRAGMA foreign_keys = ON` is set per connection on every `connect()` — SQLite defaults it off, and the `node_tags.node_id` / `relations.{src,dst}_id` FKs all depend on it.

`connect()` and `init_db()` both resolve `DEFAULT_DB_PATH` at call time (not import time) so test monkeypatches / per-project overrides actually take effect for default-arg callers.

## Hook pipeline (`src/plantrace/hooks/exit_plan_mode.py`)

1. **Read stdin as raw bytes + UTF-8 decode** with `errors="replace"`. Default `sys.stdin` on Windows uses the OEM code page (cp949 on Korean locales) and mojibake-corrupts non-ASCII plan bodies. This is empirically confirmed (`docs/evidence/`).
2. **`extract_plan_text(payload)`** — resolution order: `tool_response.plan` → `tool_response.filePath` (read file) → `tool_response.plan_file_path` / `planFilePath` aliases → `tool_input.plan`. Returns `None` if nothing resolvable. The exact payload shape is the subject of the Phase 0 spike (`roadmap.md`); this resolution order is the working hypothesis until evidence overrides.
3. **`split_children(plan_text)`** — root title = first non-empty line (strip leading `#`). Children = markdown checklist items (`- [ ]` / `- [x]`) if any, else numbered list items. If neither pattern matches, the plan stores as a single root with no children — `/why` still works.
4. **`persist_plan(...)`** — single SQLite transaction inserts root (full plan body in `body`) + N children (titles only, `plan_local_label = f"B{idx}"`). All rows carry `source_type="plan_mode"`, `source_ai="claude-code"`, a shared `source_plan_id`, and the session id truncated to 64 chars.
5. **`notion_projector.project_plan(...)`** — fail-soft. Skip cases (`no_config` / `no_token`) and HTTP errors all return `None` plus a JSONL event; the hook stays at exit 0. SQLite write already succeeded.
6. **Event log line emitted at each phase**: `received` → (`no_plan_text` or `persisted`) → (`notion.skipped_*` / `notion.projection_succeeded` / `notion.projection_failed`).

The hook never raises to the parent process. Every failure path resolves to exit 0 + a JSONL event — Phase 1A's invariant is "do not break the Claude Code session, ever".

## Notion projector (`src/plantrace/notion/projector.py`)

Page-only artifact; the Node data source comes in Phase 1B.

- **Endpoint**: `POST /v1/pages` with `parent = {type: "page_id", page_id: plan_artifact_parent_page_id}`. Subsequent `PATCH /v1/blocks/{id}/children` appends for multi-batch plans.
- **Notion API limits enforced in code**:
  - `MAX_BLOCKS_PER_REQUEST = 100` — body split into create-payload + N append-payloads.
  - `MAX_TEXT_CONTENT_CHARS = 2000` — per-`rich_text` cap; `_chunk_text` slices the plan body and `root_title` is clipped at 2000.
- **Block shape**: plan body → N `paragraph` blocks, children → `bulleted_list_item` blocks with `"[B1] <title> (n_xxxxxxxx)"` content (label omitted when child_records has no label).
- **Partial-success allowed**: a failed `blocks/children` PATCH breaks the append loop, logs `notion.projection_failed` (`stage: append`), but the page already exists and `_update_root_notion_id` still records the page id on SQLite. The first half of the plan is recoverable from Notion; the rest is recoverable from SQLite + JSONL.
- **`httpx.Client`** owned by the projector when no client is injected (test seam). Timeout: 10s read, 5s connect.

## Slash command — `/why` (`src/plantrace/slash/why.py`)

Pure local SQLite, works offline. `walk_up` follows `parent_id` until `None` or unknown id. Render shows leaf (`status`, title, plan-local label, source), then indented ancestors. Exit code 1 when the node id is unknown. The other five v0.1 slash commands are Phase 1B.

## Data persistence

| Asset | Location | Lifecycle |
|---|---|---|
| SQLite | `~/.claude/plantrace/state.db` | Canonical source of truth. Survives hook crashes (insert is committed before Notion projection starts). |
| JSONL events | `~/.claude/plantrace/logs/events-{YYYY-MM-DD}.jsonl` | Append-only raw payloads. UTC date in filename. Never rewritten. Phase 1B introduces an `events` SQLite table as the curated projection; this JSONL stays as the immutable raw trace. |
| Notion page id | `nodes.notion_page_id` (root only) | Populated by `_update_root_notion_id` after a successful create. Children get their own data_source rows in Phase 1B. |
| Notion page | Under `plan_artifact_parent_page_id` | One nested page per ExitPlanMode invocation. Title = plan root title. Phase 1B will additionally upsert per-node rows into the Node data_source. |

Vector store path (`~/.claude/plantrace/chroma`) is reserved in the schema for `classifier.mode == "embedding"` — not used in Phase 1A (manual classifier is the default, `decisions.md` row 15).

## What's deliberately not here yet

- **MCP server**: deferred until external users exist (`decisions.md` row 12 — "skill + hooks, no MCP for MVP"). v0.1 wraps the existing slash commands.
- **LangGraph state machine**: deferred to v0.2+ until 1000+ hook events accumulated (`decisions.md` row 13). Determinism after data, not before.
- **Classifier**: manual is the default; embedding mode gated behind explicit opt-in. Activates in Phase 1B after one week of personal dogfood (`decisions.md` row 15).
- **Node data_source projection**: page-only in 1A, full per-node row upsert in 1B (`decisions.md` row 16 — page parent for artifact UX, data_source parent for per-row queries).
- **Sync queue / idempotency / events table**: Phase 1B. Until then, projection is fire-and-forget and the JSONL is the durable evidence.
