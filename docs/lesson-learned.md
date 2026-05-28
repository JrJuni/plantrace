# Lessons Learned

Append-only log of approaches tried, failure causes, and validated know-how. Newest entry on top.

## Entry format

```
## [YYYY-MM-DD] One-line topic
**Tried**: which approach was taken
**Result**: success / failure + observed behavior
**Lesson**: what to do next time
```

Optional follow-up lines: `**Related files**:` and `**Related**:` (cross-link to `playbook.md` / `decisions.md` / a specific phase).

## Inclusion bar

- Real attempts only — not "I considered X". A lesson is the residue of a thing that hit the codebase or the runtime.
- Specific enough that a reader six months later can recognize the same failure mode without re-doing the diagnosis.
- If the lesson generalizes to a pattern useful outside this project, promote it to `playbook.md` and link back here.

---

## [2026-05-28] R3 외부 AI의 ExitPlanMode payload shape 주장이 절반만 사실

**Tried**: Phase 1A 코드를 v2.2 master plan의 R3 라운드 외부 AI 주장에 근거해 작성 — `tool_response.plan` (있다), `tool_response.plan_file_path` 또는 `planFilePath` (있을 수 있다)를 fallback으로 두고 `extract_plan_text`를 구현.
**Result**: Phase 0 spike instrumentation으로 첫 ExitPlanMode payload (28KB) 캡처 → `tool_response.plan`은 사실로 확인됐지만 `plan_file_path` / `planFilePath`는 부재. 실제로 존재하는 파일 경로 필드는 **`tool_response.filePath`** (camelCase). `tool_input`은 `{}` 빈 객체.
**Lesson**: 외부 모델의 payload shape 주장은 실측 evidence가 들어올 때까지 가설로만 다룬다. spike instrumentation을 본 코드보다 먼저 깔아두는 게 옳음 — Phase 0를 instrumentation 예외로 둔 결정이 정확히 의도대로 작동했다. `extract_plan_text`의 resolution order는 evidence를 보고 `filePath` 카멜케이스를 우선 fallback으로 추가하는 형태로 정정.
**Related files**: `src/plantrace/hooks/exit_plan_mode.py::extract_plan_text`, `docs/evidence/hooks.md`, `docs/evidence/hook-payloads/ExitPlanMode-20260528-143457-256.json`
**Related**: roadmap.md Phase 0

---

## [2026-05-28] Windows에서 `sys.stdin.read()`는 한글을 mojibake로 깨먹는다

**Tried**: hook 본 코드와 PowerShell spike 모두 stdin을 기본 인코딩으로 읽음 (`sys.stdin.read()` / `[Console]::In.ReadToEnd()`). Claude Code가 보내는 stdin은 UTF-8.
**Result**: Korean Windows의 OEM code page (cp949)로 디코딩되면서 한글 plan body가 mojibake로 저장됨 (`기반` → `湲곕컲`). spike에서 캡처한 28KB JSON이 처음엔 `json.loads`도 못 거치는 상태였음.
**Lesson**: Windows에서 외부 프로세스 stdin을 받을 땐 **항상 raw bytes로 받고 명시적으로 UTF-8 디코딩**. Python은 `sys.stdin.buffer.read().decode("utf-8", errors="replace")`. PowerShell은 `[Console]::InputEncoding = [System.Text.Encoding]::UTF8`을 ReadToEnd 전에 설정. `errors="replace"`로 두면 잘못된 바이트가 와도 hook은 죽지 않고 mojibake로라도 진행 — fail-soft 일관성.
**Related files**: `src/plantrace/hooks/exit_plan_mode.py::main` (raw bytes + UTF-8 decode), `scripts/echo_payload.ps1` (spike — 동일 버그를 가졌으나 P0.5에서 삭제 예정이라 미수정)

---

## [2026-05-28] Python default-arg는 함수 정의 시점에 평가된다 — 테스트 monkeypatch가 무력화됨

**Tried**: `db.connect(db_path: Path = DEFAULT_DB_PATH)` 같은 시그니처. 테스트에서 `monkeypatch.setattr(db, "DEFAULT_DB_PATH", tmp_path / "state.db")` 후 `db.connect()` 인자 없이 호출.
**Result**: monkeypatch는 모듈 속성을 갈았는데, 함수의 default arg는 **함수 정의 시점에 이미 원본 `DEFAULT_DB_PATH` 값으로 바인딩됨**. 인자 없이 부른 caller는 실제 사용자 home에 SQLite를 만드는 사고가 났다.
**Lesson**: 모듈 상수를 default arg에 직접 박지 않는다. 대신 `db_path: Path | None = None`으로 받고 함수 본문 첫 줄에서 `db_path = db_path or DEFAULT_DB_PATH`. 이렇게 하면 lookup이 매 호출마다 일어나서 monkeypatch가 효과 있음. → `playbook.md` "Default-arg path resolution at call time" 항목으로 승격.
**Related files**: `src/plantrace/db.py::connect`, `src/plantrace/db.py::init_db`, `src/plantrace/jsonl.py::event_log_path`, `src/plantrace/jsonl.py::append_event`
**Related**: `playbook.md` (재사용 패턴)

---

## [2026-05-28] 테스트 격리: `Path.home` monkeypatch만으로는 부족 — `os.path.expanduser`는 별 경로로 동작

**Tried**: `monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))`만 깔면 모든 `~/...` 경로가 tmp_path 기준으로 풀릴 거라 가정.
**Result**: `config.py`의 `_expand`는 `os.path.expanduser`를 호출하는데, Windows의 `expanduser`는 `Path.home`이 아니라 `USERPROFILE` 환경변수를 참조. monkeypatched `Path.home`을 우회해서 진짜 home으로 풀림 → 테스트가 실제 home에 SQLite/JSONL을 흘려쓰는 누설 발생.
**Lesson**: home 격리는 다중 레이어가 필요. (1) `Path.home` monkeypatch, (2) `CLAUDE_PROJECT_DIR = str(tmp_path)`로 config가 실제 `.claude/plantrace.json`을 못 읽게 차단, (3) 모듈 default 상수도 명시 monkeypatch, (4) 진짜 home plantrace 디렉터리 sentinel의 mtime을 yield 전/후 비교해서 부작용 0 검증. `os.path.expanduser` 자체를 monkeypatch하는 건 over-engineering — config가 외부 파일을 안 읽으면 expanduser도 안 불림.
**Related files**: `tests/conftest.py::tmp_home`
**Related**: `playbook.md` (sentinel mtime 검증 패턴 후보)

---

## [2026-05-28] Notion API v2026-03-11: `archived` 필드는 사라졌고 `in_trash`로 바뀜

**Tried**: 검증용으로 만든 페이지를 trash로 이동하려고 `PATCH /v1/pages/{id}` body `{"archived": true}` 호출.
**Result**: `400 Bad Request`. body로 `{"in_trash": true}`를 보내야 200.
**Lesson**: API 버전을 핀한 만큼 (`decisions.md` row 10), 필드 schema도 그 버전 기준으로 적어두지 않으면 다음 사용 시 똑같이 헷갈린다. Phase 1A projector는 page를 만들기만 하고 archive 안 하므로 코드 영향 없음 — 운영용 cleanup 시 참고.

---

## [2026-05-28] Notion integration 권한은 부모 → 자식 페이지 자동 상속되지 않는다

**Tried**: 플랜 아카이브 페이지에 `coldcall-agent` integration을 연결한 줄 알았는데, 사실은 비슷한 이름의 다른 integration (`conductor`)을 골랐었다. API는 일관되게 404 + `integration_id: 349b...` 정보를 반환.
**Result**: 첫 두 번의 hook smoke test가 `notion.projection_failed` (404). 사용자가 connection을 다시 확인하고 정확한 `coldcall-agent`로 교체하니 즉시 200.
**Lesson**: integration 권한 디버깅의 첫 단계는 **에러 응답이 알려주는 `integration_id`**가 `.env`의 token에 매칭되는지 확인. 같은 이름이라도 ID는 다를 수 있음. 또 페이지 connection은 *해당 페이지에 직접* — 부모에 걸어도 자식이 자동 상속되지 않을 수 있으니 (v2026 모델에서 명시적으로 보장 안 됨) 가장 가까운 페이지에 직접 연결.
**Related files**: `src/plantrace/notion/projector.py::project_plan` (fail-soft 404 처리), `docs/evidence/` (장기 evidence 저장소)
**Related**: roadmap.md Phase 1A E2E, `architecture.md` Notion projector section
