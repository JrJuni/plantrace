# PlanTrace

> **AI work provenance graph** — plans branch like folders, remembered like a graph.

> ⚠️ **Pre-alpha.** This repo is in active bootstrap. Phase 1A (vertical slice) is being built right now. The public install path described below is a placeholder until v0.1 ships. See [docs/roadmap.md](docs/roadmap.md) for current status. (Korean quick-read: [README.ko.md](README.ko.md))

---

## Why this exists

AI coding tools (Claude Code, Cursor, Codex, ...) churn out plans constantly. Days later, neither you nor the AI remembers *why* a particular subtask existed, *which* larger plan it belonged to, or *what* downstream things it now affects. Plain `Plan.md` files lose hierarchy. Notion pages drift. Multiple AI agents on the same workspace produce inconsistent structures.

This tool keeps a **provenance graph** — a recursive tree of every plan node every AI (and you) ever created in your project, with the source, status, and semantic tags preserved. It lives locally (SQLite, source of truth) and projects to Notion (visual layer). You can ask `/why <node>` weeks later and trace back to the original master plan.

The same problem isn't unique to software. Research, content, ops — anything an AI helps you break down into subtasks suffers the same provenance loss. The data model is general; the first lens is software-specific.

---

## Core data model

```
PlanNode (recursive tree, arbitrary depth)
├── parent_id      — folder-like hierarchy
├── status         — planned / in_progress / completed
├── source         — which plan / AI session / tool produced this node
├── relations      — ownership / influence / blocks / references (cross-cutting graph)
└── tags           — optional semantic lens (see below)
```

**Lens presets** are optional semantic overlays on top of the tree. The default for software projects is:

```
Software lens:  Vision / Domain / Module / Dev Unit
                       (Module = I/O + State + Output contract)
```

Other built-in lenses (Phase 2): **Research** (question / hypothesis / evidence / claim), **Content** (theme / section / asset / edit), **Ops** (incident / cause / mitigation / follow-up). Custom lenses via config.

---

## 5-minute demo (target shape — not yet installable)

1. `/init` — wires your Notion workspace, creates one Node data source and one Plan artifact parent page, picks a default lens.
2. In a Claude Code session, work normally. When you `ExitPlanMode`, the tool captures the plan as a `root` PlanNode + its subtasks as children, all into local SQLite + projects a Plan artifact page to Notion.
3. Run `/why <node-id>` — the tool walks parent chain + source provenance and tells you why this task exists and where it came from.

---

## Slash commands

**v0.1 (6 commands)**

Core (work in every lens):

| Command | What it does |
|---|---|
| `/why <node-id>` | Walk parent chain + show source provenance |
| `/impact <node-id>` | Traverse relations (ownership/influence/blocks/references) |
| `/orphans` | Nodes with no parent (and not root), or no lens tag |
| `/sync` | Force local↔Notion sync + drift detection |

Software lens only:

| Command | What it does |
|---|---|
| `/coverage <node-id>` | Children + expected items (per Software lens) not yet completed |
| `/stale` | Children completed *before* their parent node's body was last edited (regression risk) |

**Phase 2 addition**: `/resume <plan-id>` — auto-inject the unfinished children of a plan back into a fresh Claude Code context.

---

## Compatibility

- **Claude Code**: full support (hooks + skills + slash + MCP).
- **Other clients (Cursor, Cline, Codex, Warp, ...)**: **not supported yet** — planned for v0.2+. MCP tools may technically respond from other clients, but this release does not test or document that path.

---

## Install

_Coming with v0.1. See [docs/roadmap.md](docs/roadmap.md)._

```
# Placeholder — not yet functional
# /plugin install plantrace
```

---

## Documentation

- [docs/roadmap.md](docs/roadmap.md) — Now / Next / Later phases with exit criteria
- [docs/decisions.md](docs/decisions.md) — Active design decisions with Revisit triggers
- [docs/architecture.md](docs/architecture.md) — Surfaces, SQLite schema, hook pipeline, Notion projector
- [docs/notion_db_schemas.md](docs/notion_db_schemas.md) — Plan artifact page (shipped) + Node data_source (Phase 1B)
- [docs/commands.md](docs/commands.md) — Phase-by-phase command catalog (hooks, slash, dev/smoke)
- [docs/playbook.md](docs/playbook.md) — Reusable patterns keyword index
- [docs/lesson-learned.md](docs/lesson-learned.md) — Append-only log of what was tried and what stuck
- [docs/security-audit.md](docs/security-audit.md) — Checklist + audit history
- [docs/evidence/](docs/evidence/) — Empirical findings (hook payloads, Notion API behavior)
- [README.ko.md](README.ko.md) — 한국어 빠른 확인용 (canonical은 영문판)

---

## License

MIT — see [LICENSE](LICENSE).
