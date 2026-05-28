# PlanTrace — Phase 1A 후속 작업 plan (2026-05-28)

**컨텍스트**: `vast-foraging-whisper.md` v0.3.2의 Phase 0 + 1A 코드 작업은 완료 (commits `32b4b8b`, `304bc8c`). E2E manual smoke까지 통과 — Notion `coldcall-agent` integration이 플랜 아카이브에 연결되어 page 생성 / SQLite UPDATE / JSONL `notion.projection_succeeded` 모두 검증됨. 정리 후 SQLite 상태는 0 nodes, Notion 테스트 페이지는 trash 이동.

이 plan은 그 위에 남은 **자투리 작업**을 모은 짧은 cleanup 목록. 새로운 phase가 아니라 1A의 미진한 부분 + 1B 진입 전 사전조건.

---

## 1. Phase 0 closure (P0.4 + P0.5)

**상태**: TodoWrite 자연 캡처 미발생 — 이 세션은 `TaskCreate`(다른 도구)만 사용해 spike가 트리거되지 않음.

**할 일**:
- 다음 작업 세션에서 Claude Code가 자연스럽게 TodoWrite를 호출하면 spike가 `docs/evidence/hook-payloads/TodoWrite-*.json`에 캡처
- 캡처 직후:
  1. `docs/evidence/hooks.md`의 TodoWrite 섹션 TBD 채우기 (full snapshot vs diff, 페이로드 키)
  2. `.claude/settings.json`에서 TodoWrite matcher 블록 제거
  3. `scripts/echo_payload.ps1` 삭제
  4. `docs/evidence/hooks.md` TBD 0개로 마감
- commit 메시지 권장: `Phase 0 closure — TodoWrite evidence captured, spike removed`

**Exit**: `Get-ChildItem docs\evidence\hook-payloads\TodoWrite-*.json` 1개+, `Select-String -Path docs\evidence\hooks.md -Pattern "TBD"` 빈 결과, `.claude/settings.json`에 ExitPlanMode matcher만 남음.

---

## 2. Phase 1A E2E의 진짜 마지막 한 줄 (P1.7 보강)

**상태**: 동일한 stdin shape로 Python subprocess 통해 hook 동작은 입증 — but 실제 Claude Code `plan mode → ExitPlanMode` 경로는 본 세션에서 아직 안 거침.

**할 일**:
- 다음 세션에서 의도적으로 plan mode 진입 (`/plan` 또는 ExitPlanMode가 발동되는 task) → 작은 plan 작성 → exit
- 자동 트리거된 `.claude/settings.json` ExitPlanMode matcher → `python -m plantrace.hooks.exit_plan_mode` 실행 확인
- `$env:USERPROFILE\.claude\plantrace\logs\events-*.jsonl` 끝 줄에 `notion.projection_succeeded` 라인 존재 확인
- Notion 플랜 아카이브에 새 nested page 눈으로 확인
- 본인 사용감 메모 ("느낌 온다" 또는 불편한 부분) → `docs/lesson-learned.md`에 1줄 append

**Exit**: 실제 Claude Code 트리거 1회 성공 + 사용감 메모.

---

## 3. 오프라인 `/why` 검증 (P1.7 항목 5)

**상태**: 코드상 SQLite read-only라 네트워크 영향 없음이 구조적으로 보장 — but 명시적으로 측정 안 됨.

**할 일**:
- Phase 1A E2E 직후 새 root_id 메모
- 네트워크 차단 (WiFi off 또는 `Disable-NetAdapter`) → `plantrace-why <child-id>` 재실행 → 동일 출력 확인
- 결과 `docs/evidence/`에 짧은 메모 commit (옵션)

**Exit**: 오프라인 동작 1회 확인.

---

## 4. NOTION_TOKEN persistent 처리

**상태**: 프로젝트 `.env`로 hook 동작은 OK — but PowerShell 일반 세션 (`plantrace-why` 호출 등)에서는 token이 안 잡힘.

**할 일**:
- 사용자 판단: 더 영구적으로 두려면 `setx NOTION_TOKEN '<value>'` (User scope) 한 번 실행
- 아니면 그대로 `.env`만 유지 (hook 한정 동작 — Phase 1A에서는 충분)
- `docs/security-audit.md`에 "Token storage: project-local .env + workspace integration coldcall-agent 재사용" 한 줄 기록 (정보성)

**Exit**: 결정 + 1줄 기록.

---

## 5. extract_plan_text의 filePath fallback 테스트 추가 (P0.2 follow-up)

**상태**: 코드는 `tool_response.filePath` 카멜케이스 fallback을 이미 가짐 — but `tests/test_phase_1a.py`에는 카멜케이스 케이스가 없음. 기존 test는 snake_case `plan_file_path`만 검증.

**할 일**:
- `tests/test_phase_1a.py::test_extract_plan_text_from_file_path`를 parametrize 또는 두 번째 테스트 추가:
  - `{"tool_response": {"filePath": str(f)}}` 입력 → 파일 내용 반환
- 1줄 commit.

**Exit**: pytest 20+ green.

---

## 6. Phase 1B 진입 전 박제 (코드 작업 아님 — design only)

**조건 — 코드 시작 전 docs/decisions.md에 박제 필수**:
1. **`events` 테이블 schema**: `(event_id, idempotency_key, occurred_at, applied_at, payload_json, status)`. idempotency_key = `(event_type, internal_id, payload_hash)`.
2. **Sync queue 정책**: exponential backoff, max 3회 retry, base 1초. duplicate handling 표 (`status 변경 = last-write-wins`, `create = idempotency 매치 시 무시`).

**할 일**:
- Phase 1B 본격 시작 직전 한 차례 design discussion → decisions.md에 2개 active row 추가
- 그 다음 1B 코드.

**Exit**: decisions.md에 위 2개 항목 active로 박제.

---

## 7. Notion API 작은 발견 사항 정리 (참고용)

세션 중 알게 된 v2026-03-11 API 특이점 — 향후 implementation 시 잊지 않도록 `docs/lesson-learned.md` 또는 `docs/architecture.md`에 추가:

- **`archived` → `in_trash`**: v2026 API에서 페이지 trash 이동은 `PATCH /v1/pages/{id}` body로 `{"in_trash": true}`. 기존 `{"archived": true}`는 400 반환.
- **Integration 권한**: page connection이 부모-자식 자동 상속하지 않음. plan_artifact_parent_page_id에 직접 connect 필요.
- **ExitPlanMode `tool_response.filePath`** (camelCase): R3가 주장한 `plan_file_path` / `planFilePath`는 부재. 실제 필드명 `filePath`.

**Exit**: 위 3개 발견 사항을 적절한 doc에 1-2줄씩 append.

---

## 명시 제외 (이 plan에서 안 함)

- Phase 1B 본 코드 (classifier, /impact/orphans/sync/coverage/stale, TodoWrite hook 영구 wiring, Node data source projection)
- 외부 사용자 onboarding 문서
- ChromaDB / embedding
- MCP 패키징

---

## 우선순위 추천

1. (선택) §2 실제 Claude Code E2E — 한 사이클만 돌리면 본인 사용감 확보
2. §1 Phase 0 closure — TodoWrite가 자연스럽게 나오면 즉시
3. §5 filePath 테스트 — 5분 작업, code hygiene
4. §7 API 발견 정리 — 5분 작업, 향후 참조용
5. §3, §4 — 사용감 결정에 따라
6. §6 — Phase 1B 진입 결정 후
