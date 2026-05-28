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
| `default-arg` `testability` `module-constant` | [Default-arg path resolution at call time](#default-arg-path-resolution-at-call-time) | Don't bind module-level `Path` constants as default args — resolve `path or DEFAULT_PATH` inside the function so test monkeypatches stick. |
| `hook` `fail-soft` `non-breaking` `event-log` | [Hook process never breaks the caller](#hook-process-never-breaks-the-caller) | Every failure path (parse error, missing input, HTTP error) → exit 0 + a JSONL event line. Caller (Claude Code session) must never observe a non-zero hook exit. |
| `secret-loading` `dotenv` `lazy-import` `test-friendly` | [Lazy `load_dotenv(override=False)` at entry point](#lazy-load_dotenv-at-entry-point) | Hook reads `.env` on each invocation via lazy-imported python-dotenv. `override=False` means tests' `monkeypatch.setenv` always wins. |
| `test-isolation` `home-leak` `sentinel-mtime` | [Sentinel mtime invariance for home-leak test isolation](#sentinel-mtime-invariance-for-home-leak-test-isolation) | Instead of forbidding the real home dir from existing, capture its mtime pre-test and assert unchanged post-test. Survives concurrent dogfood writes. |

When entries grow, re-sort by tag alphabetical order. Remove only when a pattern is invalidated (and record why).

---

## Default-arg path resolution at call time

**Tags**: `default-arg` `testability` `module-constant`
**Validated**: Phase 1A — `db.connect()` / `db.init_db()` / `jsonl.event_log_path()` / `jsonl.append_event()`. Test fixture monkeypatches the module-level `DEFAULT_DB_PATH` / `DEFAULT_LOG_DIR` and inarg-less calls correctly pick up the patched value.

**The pattern**:

```python
DEFAULT_DB_PATH = Path.home() / ".claude" / "plantrace" / "state.db"

def connect(db_path: Path | None = None) -> sqlite3.Connection:
    # Resolve at call time, NOT bind at function definition.
    db_path = db_path or DEFAULT_DB_PATH
    ...
```

**Why**:
- Python evaluates default args once at function definition. `def f(x=MODULE_CONST)` captures `MODULE_CONST`'s value at the *def* moment, not at call.
- If a test does `monkeypatch.setattr(module, "MODULE_CONST", new_value)`, callers that pass `x` explicitly see the new value; callers that omit `x` still see the original. That asymmetry is the bug.
- The cure: take `Path | None = None` and resolve `path or MODULE_CONST` inside the body. Now every call re-reads the module attr.

**Where to reach for it**: any module that exposes a sensible default path/dir/URL and wants tests to be able to redirect it without per-call argument plumbing.

**Don't use when**: defaults are truly compile-time constants (math, regex patterns). Only the late-bound, environment-derived ones need this.

**Lesson root**: `lesson-learned.md` → "Python default-arg는 함수 정의 시점에 평가된다".

---

## Hook process never breaks the caller

**Tags**: `hook` `fail-soft` `non-breaking` `event-log`
**Validated**: Phase 1A — `src/plantrace/hooks/exit_plan_mode.py::main` + `src/plantrace/notion/projector.py::project_plan`. Manual smoke test exercised every failure branch (parse error from BOM-prefixed input, no_plan_text from empty payload, 404 from missing integration permission, 5xx mocked) — hook returned `0` and emitted a JSONL line in all cases.

**The pattern**:

Three failure tiers, all funneled to `exit 0 + JSONL event`:

| Failure | Event | Hook exit |
|---|---|---|
| stdin not valid JSON | `exit_plan_mode.parse_error` | 0 |
| JSON parses but no resolvable plan text | `exit_plan_mode.no_plan_text` | 0 |
| Plan persisted, Notion projection config absent | `notion.skipped_no_config` | 0 |
| Plan persisted, `NOTION_TOKEN` env missing | `notion.skipped_no_token` | 0 |
| Plan persisted, Notion HTTP non-2xx | `notion.projection_failed` (status_code + truncated body) | 0 |
| Plan persisted, Notion projector raised | `notion.projection_exception` (truncated error) | 0 |

The invariant: **SQLite write is the only success condition**. Everything downstream is optional projection. The hook's job is to not break the user's editor session.

**Why this matters**:
- A hook that raises causes Claude Code (or any caller) to surface a red error mid-session — terrible UX for an instrumentation tool the user is supposed to forget about.
- Silent failure modes are observable through the JSONL stream, which Phase 1B's `/sync` will use as the re-try entry point. So fail-soft is not "swallow" — it's "defer".

**Where to reach for it**: any non-essential side-effect bolted onto a primary operation (telemetry hooks, projections, mirrors, audit writes).

**Don't use when**: the side-effect IS the primary operation. Then a failure must be loud.

**Lesson root**: `lesson-learned.md` references and `decisions.md` row 17 (raw JSONL append from Phase 1A).

---

## Lazy `load_dotenv` at entry point

**Tags**: `secret-loading` `dotenv` `lazy-import` `test-friendly`
**Validated**: Phase 1A — `src/plantrace/hooks/exit_plan_mode.py::main` first lines. Manual smoke confirmed `.env`-loaded `NOTION_TOKEN` reaches the projector; pytest's `monkeypatch.setenv` correctly overrides without `.env` interference (override=False keeps env-first precedence).

**The pattern**:

```python
def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)  # env wins over .env
    except ImportError:
        pass
    ...
```

**Why**:
- **Lazy import**: python-dotenv is in the optional `[notion]` extra. If the user installed without it, the hook still runs fine — `dotenv` is only needed when projection is configured.
- **`override=False`**: tests' `monkeypatch.setenv` runs before the hook is called. With `override=False`, an env var that already exists wins over the `.env` value. This means `monkeypatch.setenv` and `monkeypatch.delenv` are honored — critical for the no-token test path.
- **At entry point, not at projector**: putting `load_dotenv` inside the projector would still work for Notion, but the hook may want to read other env vars later (LANG, claude-code-specific). Loading once at main() centralizes secret sourcing.

**Where to reach for it**: any CLI / hook that needs a secret/setting from a project-local file but also must respect explicit env-var overrides.

**Don't use when**: the same process is long-running and the `.env` could change at runtime — `load_dotenv` is one-shot. (For our use case, the hook process is short-lived, so this is moot.)

**Lesson root**: `lesson-learned.md` (no dedicated entry — pattern emerged during integration testing).

---

## Sentinel mtime invariance for home-leak test isolation

**Tags**: `test-isolation` `home-leak` `sentinel-mtime`
**Validated**: Phase 1A — `tests/conftest.py::tmp_home`. After tightening (`CLAUDE_PROJECT_DIR = tmp_path` + `delenv NOTION_TOKEN`), 19/19 tests pass with sentinel check active.

**The pattern**:

```python
SENTINEL = Path.home() / ".claude" / "plantrace"

@pytest.fixture(autouse=True)
def tmp_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(_db, "DEFAULT_DB_PATH", tmp_path / ".claude" / "plantrace" / "state.db")
    monkeypatch.setattr(_jsonl, "DEFAULT_LOG_DIR", tmp_path / ".claude" / "plantrace" / "logs")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.delenv("NOTION_TOKEN", raising=False)

    before = SENTINEL.stat().st_mtime if SENTINEL.exists() else None
    yield tmp_path
    after = SENTINEL.stat().st_mtime if SENTINEL.exists() else None

    if before is None:
        assert after is None, "test created real-home dir — fixture failed"
    else:
        assert before == after, "test mutated real-home dir — fixture failed"
```

**Why**:
- Forbidding the real-home dir from existing makes test runs **destructive of dogfood data**. The user can't both use the tool and run tests on the same machine.
- mtime check accepts an *existing but untouched* home — exactly what dogfood usage produces.
- Multiple monkeypatches stack defense-in-depth: `Path.home` + module defaults + `CLAUDE_PROJECT_DIR`. Any one isn't enough (`os.path.expanduser` on Windows uses `USERPROFILE`, not `Path.home`; config reads project_dir from env, not cwd).
- `delenv("NOTION_TOKEN")` neutralizes inherited shell env so tests don't accidentally fire real Notion HTTP calls.

**Where to reach for it**: tests that exercise code touching user-scoped paths (`~/.config/`, `~/Library/`, `%APPDATA%`) where the user might also be actively using the same paths.

**Don't use when**: the test only writes to tempfiles never reaches the home heuristic (e.g., explicit-path-only APIs).

**Lesson root**: `lesson-learned.md` → "테스트 격리: `Path.home` monkeypatch만으로는 부족".
