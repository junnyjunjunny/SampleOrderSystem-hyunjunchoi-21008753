# CLAUDE.md

SampleOrderSystem 작업 시 Claude Code가 따르는 규칙. 요구사항/도메인 설계는 [PRD.md](PRD.md) 참고.

## 작업 진행 방식 (필독)

- 기능 요청을 받으면 바로 코드를 수정하지 않는다. 먼저 방향(요구사항 해석, 설계 옵션, 영향 범위)을 사용자와 충분히 토론한다.
- 사용자가 명시적으로 "수정해", "진행해" 등 최종 컨펌을 준 뒤에만 실제 코드 수정을 시작한다.
- 토론 없이 바로 구현하지 않는다. 방향에 대한 이견이나 모호한 부분이 있으면 구현 전에 반드시 질문한다.
- 구현은 [test-driven-development 스킬](.claude/skills/SKILL.md)의 RED-GREEN-REFACTOR를 따르되, human-in-the-loop 확인 시점을 아래처럼 둔다.

### RED — 목표 설정 & Plan.md
1. 기능 요청의 목표를 정확히 정의한다(토론 포함).
2. [PLAN_TEMPLATE.md](PLAN_TEMPLATE.md)를 복사해 `Plan.md`를 작성하고 사용자 검토를 요청한다: 목표, 접근 방식, 영향받는 파일, 작성할 실패 테스트 목록, Action 단계의 검증 방법.
3. 사용자 승인 후 `Plan.md`를 커밋한다 (`docs(plan): <기능명> 계획`).
4. 승인된 계획대로 실패하는 테스트를 작성하고, 실제로 실패하는지 확인한다.

### GREEN — 구현
1. RED에서 합의된 목표를 달성하는 최소 구현을 작성한다.
2. 테스트가 실제로 통과하는지 `python -m unittest discover tests`로 확인한다.
3. 이 단계에서는 커밋하지 않는다. Review를 먼저 받는다.

### REVIEW — 검토 후 커밋
1. GREEN 단계 코드를 사용자와 함께 리뷰한다: `Plan.md`에 없던 내용이 구현되지 않았는지, 리팩터링이 필요한 부분은 없는지 확인한다.
2. 리팩터링이 필요하면 요청받아 반영하고, 테스트가 계속 통과하는지 재확인한다.
3. 사용자 확인이 끝나면 그때 커밋한다 (`feat(...)`/`fix(...)` 등 Conventional Commits 형식).

## 구조

```
app/
  db.py          # SQLite 연결 및 스키마 초기화 (samples, orders)
  models.py      # Sample, Order 데이터클래스
  repository.py  # SampleRepository, OrderRepository: Create/Read/Update/Delete
  services.py    # OrderService: 주문 상태 전이 및 재고 검증 규칙
  cli.py         # 콘솔 메뉴 / 입출력
main.py          # 진입점
tests/           # in-memory sqlite 기반 단위 테스트
```

## 코딩 컨벤션

- 비즈니스 규칙(상태 전이, 주문 승인/출고 시점의 재고 비교·차감 같은 도메인 규칙)은 `services.py`에만 둔다. `cli.py`와 `repository.py`에는 넣지 않는다.
- 필드 자체의 구조적 유효성(생성 시점 불변식, 예: 값의 범위·양수 여부)은 `models.py`의 `__post_init__`에 둔다. 여러 엔티티에 걸친 규칙이나 시점에 따라 달라지는 규칙(예: 승인 시점 재고 비교)은 `services.py`로 간다.
- 잘못된 입력/상태는 `ValueError` 또는 `KeyError`를 던진다. 캐치는 각 메뉴 루프 자신의 최상위에서만 한다(예: 메인 메뉴는 `run()`의 루프에서, 시료 관리 하위 메뉴는 `sample_management_menu()`의 루프에서 각각 캐치). 하위 함수(`register_sample` 등)에서 미리 조건 검사 후 `print`+`return`으로 눙치지 않는다.
- 콘솔 UX: 각 메뉴 루프는 다시 그릴 때마다 화면을 지운다(`clear_screen()`, `os.system("cls")`). 목록성 데이터는 5개씩 페이지네이션(`paginate()`)하고 `N`/`B`로 이동한다. 액션 실행 후에는 결과를 보여준 채로 `pause()`(Enter 대기)한 뒤 화면을 지운다.
- 주석은 WHY가 비자명할 때만 최소한으로 작성한다. 함수/클래스 설명용 docstring은 꼭 필요한 경우가 아니면 생략한다.
- 새 기능을 추가할 때 PRD.md의 "다음 단계로 미룸" 항목에 있으면, 먼저 PRD.md를 업데이트한 뒤 구현한다.

## 테스트

- 프레임워크: `unittest` (기존 PoC와 동일하게 유지).
- 실행: `python -m unittest discover tests`
- DB 관련 테스트는 파일 DB가 아닌 in-memory sqlite(`sqlite3.connect(":memory:")`)로 격리한다.
- 새 기능은 최소 1개 이상의 실패 케이스(잘못된 상태 전이, 재고 부족 등)를 테스트에 포함한다.

## 실행

```
python main.py
```

## 커밋 규칙 (Conventional Commits)

`<type>(<scope>): <description>` 형식을 사용한다.

- `feat`: 새 기능
- `fix`: 버그 수정
- `test`: 테스트 추가/수정
- `docs`: 문서(README/PRD/CLAUDE.md) 변경
- `refactor`: 동작 변화 없는 구조 개선
- `chore`: 빌드/설정 등 기타

예: `feat(order): 주문 승인/거절 상태 전이 구현`

## Harness (Claude Code 운영)

- 코드 변경 후에는 `python -m unittest discover tests`로 검증한다.
- 도메인 규칙을 바꾸는 변경은 PRD.md의 해당 표/흐름도를 함께 갱신한다.
- 커밋 전 `/code-review` 또는 동등한 리뷰로 CleanCode 위반(불필요한 추상화, 미사용 코드, 방어적 코드 과다 등) 여부를 확인한다.

### AI 선(先) 검증 원칙

AI가 만든 코드를 인간이 리뷰하기 전에, AI 스스로 충분히 테스트되어 있어야 한다. 사람은 "다 통과된 결과"를 검토하는 것이지, 통과 여부 자체를 대신 확인해주는 역할이 아니다.

`Plan.md`(작성은 [PLAN_TEMPLATE.md](PLAN_TEMPLATE.md) 참고)의 Action 단계에는 반드시 검증 방법을 함께 지시한다.
- **기본**: 동작 검증(Correctness) — 새/변경된 기능이 요구사항대로 동작하는지 테스트로 증명.
- **필요 시**: 사람이 최종 확인해야 할 항목을 AI가 먼저 선행 검증해서, 리뷰 시점에는 "확인만 하면 되는" 상태로 만든다.
- **필요 시**: `/tmp` 등 격리된 경로에서 공격적인 Safety Test(비정상 입력, 경계값, 악의적 입력 등)를 수행하도록 지시한다.

### 사이클마다 수행하는 SubAgent 리뷰

Test가 정상적으로 통과한 이후, 아래 4개 SubAgent(`.claude/agents/` 참고)로 코드 리뷰를 진행한다. RED-GREEN 사이클마다(즉 `Plan.md` 하나가 완료될 때마다) 반드시 거친다.

| SubAgent | 이름 | 역할 |
|---|---|---|
| SubAgent1 | `doc-consistency-verifier` | 문서 정합성 검증 — PRD.md/README.md/CLAUDE.md와 실제 구현이 어긋나지 않는지 확인 |
| SubAgent2 | `ai-action-executor` | AI Action — `Plan.md`에 따라 구현이 계획대로 수행됐는지, 범위를 벗어난 변경이 없는지 확인 |
| SubAgent3 | `test-verify` | Test Verify — 테스트가 실제로 실패→통과했는지, 커버리지 공백은 없는지, 필요 시 Safety Test 결과 확인 |
| SubAgent4 | `compliance-verify` | Compliance Verify — CLAUDE.md 규칙(작업 진행 방식, 코딩 컨벤션, 커밋 규칙) 준수 여부 확인 |

4개 SubAgent 리뷰가 모두 통과한 뒤에 사람에게 최종 리뷰를 요청하고, 승인이 나야 REVIEW 단계의 커밋을 진행한다.
