# Notion DB Schemas

Canonical Notion schema reference. PlanTrace projects two distinct surfaces, each chosen on purpose (`decisions.md` row 16 — "Plan artifact = page parent; Node = data_source parent").

- **Plan artifact pages** (Phase 1A, **shipped**): one nested page per ExitPlanMode invocation. Pure UX surface — humans browse plans like documents.
- **Node data_source** (Phase 1B, **planned**): one row per PlanNode. Queryable, status-toggle-able, the engine room for `/coverage` / `/stale` / `/orphans` / `/impact`.

> The two surfaces live under different Notion parents so their UX affordances stay coherent. A "Plan" feels like a page (read it top-to-bottom); a "Node" feels like a row (filter / sort / update status).

API version is pinned to **`2026-03-11`** (`decisions.md` row 10). Schema keys use `*_data_source_id` (not `*_database_id`) per the 2025-09-03 Notion API split — properties live on the data_source object, not the database wrapper.

## 1. Plan artifact page (Phase 1A — shipped)

**Parent**: a Notion **page** referenced by `notion.plan_artifact_parent_page_id` in `.claude/plantrace.json`.

**Per-invocation child page properties**:

| Property | Notion type | Value | Notes |
|---|---|---|---|
| `title` | title | root PlanNode title | First non-empty line of the plan body, leading `#` stripped, clipped to 2000 chars |

A page parent only supports the `title` property — there is no schema to declare. Everything else lives in the page body as blocks.

**Per-invocation child page body** (in order):

1. **Plan body as `paragraph` blocks** — the full plan markdown chunked into 2000-char slices (Notion's per-`rich_text` limit). One paragraph per slice.
2. **Children summary as `bulleted_list_item` blocks** — one bullet per parsed child PlanNode, content `"[B1] <child title> (n_xxxxxxxx)"` (label omitted when no `plan_local_label` is present).

**Append batching**: first batch lands in the `POST /v1/pages` create call (up to `MAX_BLOCKS_PER_REQUEST = 100`). Overflow lands in subsequent `PATCH /v1/blocks/{id}/children` calls, also 100-block-batched. A partial append failure breaks the loop but the page already exists — the SQLite root row's `notion_page_id` is still updated. Recoverable.

**Reference**: `src/plantrace/notion/projector.py`.

## 2. Node data_source (Phase 1B — planned, not yet implemented)

**Parent**: a Notion **data_source** referenced by `notion.node_data_source_id` in `.claude/plantrace.json`. Bootstrapped by the future `/init` (Phase 2) command; until then this id is a placeholder.

> The schema below is the proposed Phase 1B shape, anchored to the SQLite `nodes` / `node_tags` / `relations` tables. Properties marked `(rollup)` are computed locally and projected as page properties — Notion's rollup API is read-only (`decisions.md` row 11).

### Properties

| Property | Notion type | Source | Notes |
|---|---|---|---|
| `Title` | title | `nodes.title` | Identical to SQLite. Notion's unique title constraint is not relied upon — `internal_id` is the canonical key. |
| `Internal ID` | rich_text | `nodes.internal_id` | The stable key (`n_xxxxxxxx`). The `decisions.md` row 19 commitment — internal id is the identity, lens label + plan-local label are computed/UX. |
| `Plan-local label` | rich_text | `nodes.plan_local_label` | Paste-friendly lingua franca (e.g. `B1`, `B2`). Same as the original plan-mode output line. |
| `Status` | select | `nodes.status` | 3 options with icon mapping per `decisions.md` row 4: `planned` ⚪ / `in_progress` 🟡 / `completed` ✅. No `blocked` / `cancelled` until 5+ real cases demand them. |
| `Parent` | relation | `nodes.parent_id` → same data_source | Self-referencing relation. The tree axis (vs. the `relations` graph axis). |
| `Lens tag` | select or multi_select | `node_tags` where `tag_kind = 'lens'` | Per-lens options. Software lens: `vision` / `domain` / `module` / `dev_unit`. Determined by `lenses.<key>.values` in the config — `/init` writes the matching select options at workspace setup. |
| `Topic tags` | multi_select | `node_tags` where `tag_kind = 'topic'` | Free-form semantic tags. Options created on demand. |
| `Source type` | select | `nodes.source_type` | E.g. `plan_mode`, `todo_write`, `manual`. |
| `Source AI` | rich_text | `nodes.source_ai` | E.g. `claude-code`, `cursor`. |
| `Source plan ID` | rich_text | `nodes.source_plan_id` | Shared across all rows from the same ExitPlanMode invocation — lets a Notion filter rebuild the original plan grouping. |
| `Plain language` | rich_text | `nodes.plain_language` | The first-class plain-language layer (`decisions.md` row 14). Populated by Phase 1B classifier or manual edit. |
| `Created at` | created_time / date | `nodes.created_at` (epoch seconds) | Use Notion's built-in `created_time` when the data_source row's create-time aligns with the node create-time; otherwise a custom `date` property. |
| `Completed at` | date | `nodes.completed_at` | Nullable. Drives `/stale` (children completed before parent body's last edit). |
| `Contract coverage` (rollup-style) | number | computed locally | The `decisions.md` row 11 commitment — projection writes the precomputed number as a page property. Notion's rollup API is read-only so we cannot delegate it. |
| `Relations: ownership` | relation | `relations` where `relation_type='ownership'` and `src_id = this.internal_id` | 4 separate Notion relation properties, one per `relation_type` (`decisions.md` row 5). Filterable independently in Notion UI. |
| `Relations: influence` | relation | same, `relation_type='influence'` | |
| `Relations: blocks` | relation | same, `relation_type='blocks'` | |
| `Relations: references` | relation | same, `relation_type='references'` | |

### Why this shape

- **Parent relation + four typed relations** preserve the tree / graph split from `decisions.md` row 7. The parent axis is what humans navigate; the four relations are the cross-cutting graph that `/impact` traverses.
- **Per-`relation_type` Notion relation properties** (rather than a single typed `select`) let the Notion UI filter and group by relation kind without writing a database view per kind.
- **No `internal_id` title trick**: putting the internal id in `Title` would collapse Notion's headline UX. Title is human-readable; `Internal ID` is the system-of-record key in its own property.
- **`Contract coverage` is computed, then projected**: the SQLite source of truth runs the rollup; Notion just renders the number. Avoids round-trips and stays consistent across surfaces.

### Sync model

- **Source of truth**: SQLite. `decisions.md` row 8. Notion is a projected view.
- **Sync queue + idempotency** lives in the Phase 1B `events` table. Until that table lands, the projector is fire-and-forget and the JSONL event log is the durable evidence (`decisions.md` row 17).
- **`/sync`** (Phase 1B) walks SQLite, compares against Notion, and re-projects any drift. Drift detection criteria: status mismatch, missing relation rows, stale rollup.

### Bootstrap (Phase 2 `/init`)

`/init` will:
1. Create one new Notion data_source under the user-selected parent — schema defined by `database_schema()` in code, properties applied via `data_sources.create` (post-2025-09-03 API: properties live on the data_source, not the database wrapper).
2. Create one new Notion page (the "Plan artifact parent page") as a sibling of the data_source.
3. Write both ids into `.claude/plantrace.json` under `notion.node_data_source_id` and `notion.plan_artifact_parent_page_id`.
4. Pick a default lens (from `project_type`) and apply matching `Lens tag` select options.

Before Phase 2 lands, both ids are user-provided (paste the database / page ids from Notion's share menu).

## Out of scope (deferred)

- **Per-row icon write rate limit** — open question in `decisions.md`. Will measure during Phase 1B verification.
- **Reverse-sync (Notion → SQLite)** — not in scope until external users edit nodes directly in Notion. SQLite stays one-way authoritative for v0.1.
- **Lens-specific Notion views** — Notion view filtering can be configured by the user once the data_source exists; PlanTrace won't generate views in v0.1.
