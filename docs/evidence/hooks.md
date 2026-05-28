# Phase 0 Spike — Hook Payload Evidence

**Status**: ExitPlanMode captured + analyzed (2026-05-28). TodoWrite pending natural trigger.

## Instrumentation

- Hook config: `.claude/settings.json` (project-scope, two matchers after P0.3 split)
- Capture script (TodoWrite spike only after P0.3): `scripts/echo_payload.ps1` writes raw stdin to `docs/evidence/hook-payloads/{tool}-{timestamp}.json`
- Cleanup: once `TodoWrite-*.json` exists and this doc has zero TBDs, remove TodoWrite matcher block + delete the script.

## What we want to confirm

1. Does the `ExitPlanMode` PostToolUse payload include `plan` and/or `planFilePath` (or `tool_response.plan`)?
2. Does the `TodoWrite` payload deliver only the full new list, or also a diff vs. the previous state?
3. What is the practical payload size limit?
4. What is the default hook timeout?

## Captured payloads

### ExitPlanMode

Sample: `docs/evidence/hook-payloads/ExitPlanMode-20260528-143457-256.json` (28,821 bytes; this plan refresh exit)

Top-level shape (UTF-8 keys):
```
{
  "session_id": "<uuid>",
  "transcript_path": "<absolute path>",
  "cwd": "<repo root>",
  "permission_mode": "auto",
  "effort": { "level": "xhigh" },
  "hook_event_name": "PostToolUse",
  "tool_name": "ExitPlanMode",
  "tool_input": {},                              // empty for ExitPlanMode
  "tool_response": {
    "plan": "<full plan markdown>",              // PRESENT — 28KB body
    "isAgent": false,
    "filePath": "C:\\Users\\...\\<plan-id>.md"   // canonical plan file on disk
  },
  "tool_use_id": "<toolu_*>",
  "duration_ms": 0
}
```

**Findings**:
- Plan body access: `tool_response.plan` (string, full markdown). R3 external AI claim **CONFIRMED** for this field.
- File path field: `tool_response.filePath` (camelCase, not `plan_file_path`). R3 claim of `plan_file_path` / `planFilePath` is **REFUTED** — neither key was present. `extract_plan_text` should also accept `filePath` as a fallback when present.
- `tool_input` is empty `{}` — the plan body never travels via tool_input for ExitPlanMode. Phase 1A `extract_plan_text`'s tool_input.plan branch is dead code (kept for safety, costs nothing).
- Korean characters in the captured file are mojibake. Root cause: `scripts/echo_payload.ps1` uses `[Console]::In.ReadToEnd()`, which decodes stdin using the system OEM code page (cp949 on Korean Windows). The Python hook (`exit_plan_mode.py::main`) has the same risk if it uses `sys.stdin.read()`; fixed to `sys.stdin.buffer.read().decode("utf-8", errors="replace")` in this same session.

### TodoWrite

_(pending — populated by P0.4 natural capture)_

```json
{}
```

**Findings**:
- Full snapshot vs diff: TBD
- Field carrying todos: TBD

## Payload size limit

ExitPlanMode #1 measured 28,821 bytes (28KB) and was delivered intact (modulo encoding). No truncation observed.

Anthropic Claude Code docs on hook stdin payload limit: TBD (look up before P0.5).

## Default hook timeout

Anthropic Claude Code default `PostToolUse` hook timeout: TBD (look up before P0.5). Phase 1A hook must complete well under it (currently O(ms) for SQLite + JSONL writes; Notion projection in P1.5 is HTTP, but fail-soft so timeout will not block the hook beyond httpx's own deadline).

## Decisions impacted

- `extract_plan_text` keeps `tool_response.plan` as primary; should also try `tool_response.filePath` (camelCase) ahead of `plan_file_path` (snake_case). Update with the snake_case alias kept as fallback for robustness. → planned in P1.5 alongside other hook edits.
- Phase 1A hook stdin must be UTF-8-decoded explicitly (already applied to `main()`).
