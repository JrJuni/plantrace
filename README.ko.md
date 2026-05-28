# PlanTrace (한국어 빠른 확인용)

> **AI work provenance graph** — 폴더처럼 쪼개고, 그래프처럼 기억한다.

> ⚠️ **Pre-alpha.** 본 repo는 현재 Phase 1A (vertical slice) 빌드 중. 아래 install 경로는 v0.1 ship 전까지 placeholder. 진행 상황은 [docs/roadmap.md](docs/roadmap.md)에서. **Canonical은 [README.md](README.md) (영문판)** — 이 문서는 빠른 참조용 축약본.

---

## 왜 만드는가

Claude Code / Cursor / Codex 같은 AI 도구가 매일 plan을 쏟아내지만, 며칠 뒤엔 본인도 AI도 "왜 이 subtask가 생겼는지 / 어느 큰 plan에 속했는지 / 지금 무엇에 영향 주는지" 못 따라간다. `Plan.md`는 hierarchy를 잃고, Notion 페이지는 drift하고, 여러 AI가 같은 workspace에 일관성 없는 구조를 만든다.

이 도구는 **provenance 그래프**를 유지한다 — 프로젝트 안에서 AI(들)와 사람이 만든 모든 plan 노드의 재귀 트리, 출처·상태·의미 태그를 보존. Local SQLite (canonical) + Notion (projection) 구조. 몇 주 뒤 `/why <node>`로 master plan까지 추적 가능.

소프트웨어에만 적용되는 문제 아님. 연구·콘텐츠·운영 등 AI가 작업을 분기시키는 모든 영역에 동일. 데이터 모델은 generic, 첫 lens는 software 특화.

---

## 핵심 데이터 모델

```
PlanNode (재귀 트리, 임의 depth)
├── parent_id      — 폴더식 계층
├── status         — planned / in_progress / completed
├── source         — 어느 plan / AI 세션 / 도구에서 왔는지
├── relations      — ownership / influence / blocks / references (cross-cutting graph)
└── tags           — optional semantic lens
```

**Lens preset** = tree 위에 얹는 optional 의미 layer. 기본값 (software project):

```
Software lens:  Vision / Domain / Module / Dev Unit
                       (Module = I/O + State + Output 컨트랙트)
```

Phase 2 built-in 추가: **Research / Content / Ops**. Custom lens는 config로.

---

## 5분 데모 (목표 모양 — 아직 install 불가)

1. `/init` — Notion workspace 연결 + Node data source 1개 + Plan artifact parent page 1개 생성 + default lens 선택
2. Claude Code 세션에서 평소대로 작업. `ExitPlanMode` 시 plan이 root PlanNode + subtask들이 children으로 자동 캡처 → SQLite 저장 + Notion Plan artifact page projection
3. `/why <node-id>` 실행 → parent chain + source provenance traversal

---

## Slash commands

**v0.1 (6개)**

Core (모든 lens에서 동작):

| Command | 기능 |
|---|---|
| `/why <node-id>` | parent chain + source provenance |
| `/impact <node-id>` | relations 따라 ownership/influence/blocks/references traversal |
| `/orphans` | parent 없는 (root 아닌) 노드, 또는 lens tag 없는 노드 |
| `/sync` | local↔Notion 강제 동기화 + drift 검출 |

Software lens 전용:

| Command | 기능 |
|---|---|
| `/coverage <node-id>` | children + (Software lens) expected items 중 not-completed |
| `/stale` | parent body가 마지막 수정된 시점 *이전*에 completed된 children (회귀 위험) |

**Phase 2 추가**: `/resume <plan-id>` — plan의 미완료 children을 새 Claude Code 세션에 자동 컨텍스트 주입.

---

## 호환성

- **Claude Code**: full (hooks + skills + slash + MCP)
- **기타 (Cursor, Cline, Codex, Warp, ...)**: **not supported yet** — v0.2+ 예정. MCP 호출은 기술적으로 가능하나 v0.1에서는 검증/문서화 X.

---

## Install

_v0.1과 함께 제공. [docs/roadmap.md](docs/roadmap.md) 참조._

---

## 문서

- [docs/roadmap.md](docs/roadmap.md) — Now / Next / Later + 각 phase exit criteria
- [docs/decisions.md](docs/decisions.md) — 활성 설계 결정 + Revisit triggers
- [docs/architecture.md](docs/architecture.md) — surface, SQLite schema, hook pipeline, Notion projector
- [docs/notion_db_schemas.md](docs/notion_db_schemas.md) — Plan artifact page (1A) + Node data_source (1B)
- [docs/commands.md](docs/commands.md) — phase 별 command 카탈로그
- [docs/playbook.md](docs/playbook.md) — 재사용 패턴 keyword index
- [docs/lesson-learned.md](docs/lesson-learned.md) — append-only 시도/교훈 로그
- [docs/security-audit.md](docs/security-audit.md) — 보안 체크리스트 + 감사 이력
- [docs/evidence/](docs/evidence/) — 실증 발견 (hook payload, Notion API 동작)

---

## License

MIT — [LICENSE](LICENSE) 참조.
