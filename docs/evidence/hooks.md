# Phase 0 Spike — Hook Payload Evidence

**Status**: instrumentation deployed, evidence pending first natural trigger.

## Instrumentation

- Hook config: `.claude/settings.json` (project-scope, matcher `ExitPlanMode|TodoWrite`)
- Capture script: `scripts/echo_payload.ps1` (writes raw stdin JSON to `docs/evidence/hook-payloads/{tool}-{timestamp}.json`)
- Cleanup: once both `ExitPlanMode-*.json` and `TodoWrite-*.json` exist and this doc is filled in, remove the `hooks` block from `.claude/settings.json` and delete the script.

## What we want to confirm

1. Does the `ExitPlanMode` PostToolUse payload include `plan` and/or `planFilePath` (or `tool_response.plan`)? (Round 3 external AI claim — needs empirical confirmation.)
2. Does the `TodoWrite` payload deliver only the full new list, or also a diff vs. the previous state?
3. What is the practical payload size limit? (Try with a large plan / long todo list.)
4. What is the default hook timeout?

## Captured payloads

_(populated on first trigger)_

### ExitPlanMode

```json
{}
```

**Findings**:
- Plan body access mechanism: TBD
- File path field: TBD

### TodoWrite

```json
{}
```

**Findings**:
- Full snapshot vs diff: TBD
- Field carrying todos: TBD

## Decisions impacted

Once captured, update `~/.claude/plans/ai-majestic-glacier.md` Phase 0 baseline section if the empirical result differs from the Round 3 external AI claim. Then proceed to Phase 1A coding with confirmed payload shape.
