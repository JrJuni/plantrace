# PlanTrace — Roadmap

> Parent document for README, config schema, decisions. The product's own roadmap is itself a graph-able artifact — eating our own dog food.

**Product identity**: AI work provenance graph — plans branch like folders, remembered like a graph.

---

## Now (Phase 0 + 1A)

### Phase 0 — Hook payload spike (instrumentation exception)
ExitPlanMode/TodoWrite hook payload empirical capture.
- **Exit**: `docs/evidence/hooks.md` answers 4 questions (plan body access, TodoWrite diff, payload size, timeout) + confirms or refutes external AI claim about `plan`/`planFilePath` fields.

### Phase 1A — Thin Vertical Slice
Root master PlanNode + child task 1+ capture → SQLite tree + JSONL raw events → Notion Plan artifact page projection → `/why`.
- **Exit**: PlanTrace's own repo plan flows end-to-end through the tool (root + N≥1 children stored as tree, `/why` traverses chain offline).

---

## Next (Phase 1B + 1.5)

### Phase 1B — Expanded MVP
- Classifier (manual default, embedding gated via `classifier.mode`)
- Remaining 5 slash commands:
  - **Core (all lenses)**: `/impact`, `/orphans`, `/sync`
  - **Software lens only**: `/coverage`, `/stale`
- Sync queue + idempotency, `events` table (formal)
- Lens system activated, Notion `1 Node data source + 1 Plan artifact parent page` operational
- **Exit**: 1 week of personal dogfood; `/why` or `/impact` provided real debugging value at least once.

### Phase 1.5 — Dogfood metric
- `docs/incident-template.md` (R1 #10)
- 2 weeks incident manual count
- **Exit**: 5+ incident notes, 1 week of frictionless use.

---

## Later (Phase 2 — OSS v0.1)

- MCP packaging
- `/init` (5-minute setup wizard)
- `/resume <plan-id>` (Phase 2 command addition — v0.1 total = 7 commands)
- Default lens presets (software / research / content / ops / generic)
- README (English canonical) + README.ko (Korean) complete
- Launch (Show HN, dev.to, LinkedIn, GeekNews, 디스콰이엇 — one-day burst)
- **Exit**: 1 external user setup → first placement in 5 minutes.

---

## Backlog (v0.2+)

- Multi-client adapter (Cursor / Codex / Warp)
- LangGraph state machine
- Telemetry opt-in
- Additional lens presets (community PRs welcome)
- **Guided Setup Agent** — superset UX over `/init`. Interviews the user to propose master plan, initial PlanNode tree, default lens, Notion workspace. v0.1 ships `/init` only.

---

## How this roadmap is itself a PlanNode tree

This document is the canonical example of how the product itself thinks. Each phase = a PlanNode. Each Exit criterion = its `completed` predicate. Each Backlog item = `status: planned` with no parent yet assigned. When the dogfood loop kicks in (Phase 1A complete), these very items will be ingested into the tool's SQLite as the bootstrap root tree.
