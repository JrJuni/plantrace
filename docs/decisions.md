# PlanTrace — Design Decisions

> Controlled change, not engraved stone. Every decision carries a Status, Date, and Revisit trigger — so we can re-open it intentionally instead of by accident.

**Source plan**: `~/.claude/plans/ai-majestic-glacier.md` v2.2 (final, 2026-05-23)

| Decision | Status | Date | Revisit trigger | Why |
|---|---|---|---|---|
| Recursive PlanNode tree = canonical model | active | 2026-05-23 | User complains tree is too deep to navigate | Folder-like intuition for humans + AI semantic tagging are separable concerns |
| 4-layer (Vision/Domain/Module/Dev Unit) = Software lens preset, not core | active | 2026-05-23 | Evidence that software-only is sufficient (no research/content/ops traction) | Multi-domain extensibility |
| Product identity = "AI work provenance graph" (not software-planning tool) | active | 2026-05-23 | Software-dev focus alone gets enough traction | Future expandability into research/content/ops |
| Status = planned / in_progress / completed (3 states) | active | 2026-05-23 | 5+ real cases needing `blocked` or `cancelled` | Simplicity first; Notion icon mapping ⚪/🟡/✅ |
| Relations = 4 kinds: ownership / influence / blocks / references | active | 2026-05-23 | 3+ real cases needing a 5th kind | Minimal expressive power |
| Lens preset system (user-extensible) | active | 2026-05-23 | Users struggle to define custom lenses | Flexibility |
| Tree (parent_id) vs Graph (relations) separated | active | 2026-05-23 | — | Simple traversal + cross-cutting concerns both representable |
| Local SQLite = source of truth; Notion = projected view | active | 2026-05-23 | Notion API rate limit relaxes (3 req/s → 10+) | Rate limit & latency bypass, deterministic query, offline-capable |
| Notion config keyed on `*_data_source_id` (not `*_database_id`) | active | 2026-05-23 | Notion API breaking change after 2025-09-03 | 2025-09-03 API split: schema properties live on data_source object |
| Notion `api_version` pinned to `"2026-03-11"` | active | 2026-05-23 | New stable version available 1+ year | API change resilience; explicit pin > "latest" |
| `contract_coverage` computed locally → projected to Notion as page property | active | 2026-05-23 | Notion exposes rollup-write API | Rollup is read-only on the API surface |
| Skill + hooks (no MCP) for MVP | active | 2026-05-23 | External users > 1 | Packaging ceremony unnecessary when caller is just me |
| LangGraph state machine deferred to v0.2+ | active | 2026-05-23 | 1000+ hook events accumulated | Determinism after data accumulates, not before |
| Plain-language layer = first-class property on every node | active | 2026-05-23 | — | Strongest product differentiator |
| Classifier = manual default, embedding behind feature gate | active | 2026-05-23 | After 1 week personal dogfood | First slice's classifier value/cost unproven |
| Plan artifact = page parent; Node = data_source parent | active | 2026-05-23 | Notion API behavior changes | Each UX needs its matching parent type |
| JSONL raw event append starting from Phase 1A | active | 2026-05-23 | When `events` table introduced in 1B — define raw retention policy | Provenance is the product's essence; preserve raw from day 1 |
| Slash commands: core (lens-agnostic) vs software-lens-only | active | 2026-05-23 | Research/content/ops lenses need additional lens-aware queries | Consistent with PlanNode generalization |
| ID structure: internal (stable) + lens_label (computed) + plan-local (B2 etc.) | active | 2026-05-23 | — | Stable ID + readable label + paste-friendly lingua franca |
| Copy-paste lingua franca = plan-mode output format preserved | active | 2026-05-23 | — | Round-trip between Notion and Claude Code feels natural |
| v0.1 = Claude Code only (other clients "not supported yet") | active | 2026-05-23 | 5+ install requests from non-Claude-Code users | Scope compression |
| Product name = PlanTrace (repo + package = `plantrace`) | active | 2026-05-23 | Trademark conflict surfaces or naming feedback at launch is uniformly negative | "Plans branch like folders, remembered like a graph" — single noun captures provenance-graph identity better than "ai-plan-manager" |

---

## Open questions (to resolve at named milestones)

- **Product naming** — required before launch (candidates: PlanGraph / WhyMap / Lattice / 궤적 / TBD)
- **Lens-aware queries beyond software** — verify during dogfood whether research/content/ops lenses need their own `/coverage`-equivalent queries
- **Notion page icon API write rate limit** — confirm during Phase 1B verification
- **`/why` output depth** — parent chain only vs. source provenance included — decide after Phase 1A self-use

---

## Deferred (with deadlines)

- Events table `idempotency_key` / retry / duplicate-handling spec — **must** be defined at Phase 1B sync queue introduction (no code before spec)
- `docs/incident-template.md` — write at Phase 1.5 (just before dogfood metric collection)

---

## Considered and Rejected

None (Rounds 1+2+3 final Drop = 0).

> Historical note: R3-8 "Guided Setup Agent" was momentarily rejected as hallucinated during v2.2 drafting, but user-confirmed as intentional. Now in v0.2+ Backlog per roadmap.
