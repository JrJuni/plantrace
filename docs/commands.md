# Commands

Phase-by-phase command catalog. The README's `## Slash commands` shows the v0.1 user-facing 6 (+ Phase 2's `/resume`); this doc covers everything else — hook entry points, dev/smoke scripts, test runners — for any phase that has work to do.

The repo currently has **no system Python requirement** at install time. The runtime hook is invoked by Claude Code via the `plantrace-hook` console script (`pyproject.toml::project.scripts`); local dev uses whatever Python the contributor has activated.

## Tests

```bash
# All unit tests
python -m pytest

# Single test
python -m pytest tests/test_phase_1a.py -v

# Notion projection tests only (mock httpx — no live API)
python -m pytest tests/test_phase_1a_notion.py -v
```

## Phase 0 — Hook payload spike

Empirical capture of the `ExitPlanMode` PostToolUse payload shape. Two paths.

```powershell
# Windows / PowerShell — drop this hook into Claude Code settings as a PostToolUse
# matcher for ExitPlanMode, then trigger ExitPlanMode in a session. The script
# writes the raw stdin JSON to docs/evidence/hook-payloads/<timestamp>.json.
scripts\echo_payload.ps1
```

The captured payloads live in `docs/evidence/hook-payloads/`. The spike's exit gate is `docs/evidence/hooks.md` answering 4 questions (plan body access / TodoWrite diff / payload size / timeout) — see `roadmap.md` Phase 0.

## Phase 1A — Hook + persistence + `/why`

Installed by `pyproject.toml::project.scripts`:

```bash
# The ExitPlanMode PostToolUse hook (Claude Code calls this via configured matcher)
plantrace-hook

# /why — trace a node's parent chain + source provenance
plantrace-why <node-id>
```

The hook is not normally invoked by hand. To smoke-test without Claude Code:

```bash
# Pipe a sample payload to the hook directly. Persists to SQLite + appends to JSONL +
# attempts Notion projection (skipped without config + NOTION_TOKEN).
type examples\sample_exit_plan_payload.json | plantrace-hook   # Windows
cat   examples/sample_exit_plan_payload.json | plantrace-hook   # macOS/Linux
```

After the hook runs, inspect:

```bash
# SQLite
sqlite3 %USERPROFILE%\.claude\plantrace\state.db "SELECT internal_id, title, status FROM nodes ORDER BY created_at DESC LIMIT 10;"

# Today's raw event log
type %USERPROFILE%\.claude\plantrace\logs\events-2026-05-28.jsonl
```

## Phase 1B — Expanded MVP (not yet implemented)

Planned slash commands (entry points TBD; will land alongside the lens system activation):

```bash
plantrace-impact   <node-id>     # walk relations (ownership/influence/blocks/references)
plantrace-orphans                # nodes with no parent (not root), or no lens tag
plantrace-sync                   # force local <-> Notion sync + drift detection
plantrace-coverage <node-id>     # Software lens: children + expected items not yet completed
plantrace-stale                  # Software lens: children completed before parent body's last edit
```

Until Phase 1B lands, treat the above as roadmap commitments, not callable commands. Track in `roadmap.md`.

## Phase 2 — OSS v0.1

```bash
plantrace-init                   # 5-minute setup wizard — Notion workspace pair + lens pick
plantrace-resume <plan-id>       # inject a plan's unfinished children into a fresh Claude Code context
```

## Notes

- The hook **never raises** to its parent process. Every failure (bad JSON, missing plan text, Notion HTTP error) lands as a JSONL event and the process exits 0. Phase 1A invariant: do not break the Claude Code session.
- All commands resolve the project root via `CLAUDE_PROJECT_DIR` env var when set (Claude Code provides it), falling back to `os.getcwd()`. The project's `.claude/plantrace.json` is found from there.
- Notion projection is opt-in: it requires both a non-placeholder `plan_artifact_parent_page_id` in `.claude/plantrace.json` AND the `NOTION_TOKEN` env var. Either missing → silent skip + JSONL `notion.skipped_*` event.
