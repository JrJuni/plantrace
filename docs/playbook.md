# Playbook

The single source of truth for **patterns judged reusable** after solving a hard problem in this codebase.

- **Relation to `lesson-learned.md`**: lessons are the "never make this mistake again" axis; playbook is the "this approach also works elsewhere" axis. Lessons come first; playbook entries are the ones worth lifting out.
- **Lookup trigger**: when you hit an error or get stuck, **grep the keyword index here first**. Confirm whether you've solved a similar problem before, then drill down to lessons / architecture / code.
- **Inclusion bar**: (1) actually validated working in this project, AND (2) reusable outside this project. One-off bug fixes don't qualify.
- **vs memory `feedback_*.md`**: playbook is for **project code/structure** patterns. Memory feedback is for **user collaboration style/preferences**. Keep the two stores distinct.

---

## Keyword Index

| Tags | Title | One-line summary |
|------|------|-----------|
| _(empty)_ | _(awaiting first entry)_ | The first entries will land after Phase 0 (hook payload spike) and Phase 1A (vertical slice) produce reusable patterns. |

When entries grow, re-sort by tag alphabetical order. Remove only when a pattern is invalidated (and record why).

---

_(No entries yet. First candidates already on the radar — write them up when validated:)_

- **Hook process never breaks the caller** — the Phase 1A invariant that every failure path (bad JSON, missing plan text, Notion HTTP error) resolves to exit 0 + a JSONL event. Tagging candidate: `hook` `fail-soft` `non-breaking` `event-log`.
- **Append-only JSONL raw + SQLite curated projection** — `decisions.md` row 17 separates the immutable raw trace from the queryable curated table. Tagging candidate: `raw-trace` `event-log` `idempotency` `dual-store`.
- **Default-arg path resolution at call time, not import time** — `db.connect()` / `jsonl.event_log_path()` re-read the default each call so monkeypatching the module-level constant in tests actually takes effect for default-arg callers. Tagging candidate: `testability` `module-constant` `default-arg`.

Promote each from `lesson-learned.md` once it's actually been used outside its first incident.
