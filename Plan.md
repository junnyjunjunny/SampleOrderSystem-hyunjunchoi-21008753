# Plan: 출고 처리(6번) 구현 + 재고 차감 시점을 승인/생산 시점으로 이동

## 목표

1. `[6] 출고 처리` 구현: `CONFIRMED` 주문 목록(번호/주문번호/고객/시료/수량)을 보여주고 번호를 선택하면 `RELEASE`로 전이.
2. 재고 차감 시점 변경: 지금까지는 출고(`ship`) 시점에 `stock -= quantity`였는데, 이를 승인/생산 시점으로 옮긴다.
   - `decide()`에서 재고가 충분해 바로 `CONFIRMED`가 되는 경우 → 그 즉시 `stock -= quantity`.
   - `PRODUCTION`이었던 주문이 `complete_production()`으로 `CONFIRMED`가 되는 경우 → 재고를 `production_quantity`만큼 채우는 동시에 `quantity`만큼 차감(순증감 = `production_quantity - quantity`).
   - `ship()`은 이제 `CONFIRMED → RELEASE` 상태 전이만 하고 재고는 건드리지 않는다.

## 접근 방식

- **services.py**
  - `decide()`의 `sample.stock >= order.quantity` 분기에서 `CONFIRMED` 전이 직후 `sample_repo.update_stock(sample_id, sample.stock - order.quantity)` 호출.
  - `complete_production()`의 재고 갱신을 `stock + production_quantity` → `stock + production_quantity - order.quantity`로 변경.
  - `ship()`에서 재고 갱신 코드 제거(상태 전이만 남김).
- **cli.py**
  - `print_release_table(orders, sample_repo)`: 컬럼 번호/주문번호/고객/시료/수량.
  - `release_menu(sample_repo, order_repo, service)`: `order_approval_menu`와 동일한 페이지네이션(5개/페이지) + 번호 입력 패턴. 번호를 고르면 곧바로 `service.ship()` 호출(승인/거절처럼 Y/N 재확인 없음 — 스펙에 없음).
  - 기존 `ship_order` 함수 제거, 메인 메뉴 `[6]` 연결을 `release_menu`로 변경.
- 재고 수식이 바뀌므로 기존 테스트(`test_confirmed_then_ship_deducts_stock`, `test_complete_production_confirms_and_restocks`) 기대값을 새 시점 기준으로 수정하고, "즉시 CONFIRMED 시 차감", "생산 완료 시 순증감", "출고는 재고 불변" 각각에 대한 테스트를 추가/보강한다.

## 영향받는 파일

- `app/services.py` — `decide`, `complete_production`, `ship` 재고 처리 위치 변경
- `app/cli.py` — `release_menu`, `print_release_table` 신설, `ship_order` 제거, 메인 메뉴 `[6]` 연결 변경
- `tests/test_services.py` — 재고 차감 시점 관련 테스트 갱신/추가
- `docs/03-주문승인거절.md`, `docs/05-생산라인조회.md`, `docs/06-출고처리.md`, `PRD.md` — 재고 차감 시점 서술 갱신

## 구현 & 검증 방법

- [x] 구현: 서비스 계층 재고 처리 이동
  - 확인: 갱신된/신규 테스트(`test_decide_confirms_and_deducts_stock_immediately`, `test_complete_production_confirms_and_settles_stock`, `test_ship_does_not_change_stock` 등)로 세 지점(즉시확정/생산완료/출고)의 재고 변화가 정확한지 확인, 전체 51/51 통과
- [x] 구현: `cli.py`의 `release_menu`
  - 확인(사람 확인 선행): 임시 DB로 CONFIRMED 주문 2건(승인 즉시 확정, 재고 100→85로 이미 차감된 상태) 생성 → 목록/번호 선택 출고 → 주문1 출고 후 목록에서 사라지고 상태 `RELEASE`로 확인, 재고는 그대로 85(출고가 재고를 건드리지 않음) 확인

## 가벼운 자체 점검 (커밋 전, 필수)

- [x] 문서 정합성: docs/03, 05, 06, PRD.md가 실제 구현과 일치하도록 갱신
- [x] 범위 준수: 다른 메뉴/로직 변경 없음
- [x] 테스트: 51/51 통과, 재고 차감 시점 변경에 대한 실패/경계 케이스 포함
- [x] 컨벤션 준수: 재고 계산은 services.py에, cli.py는 표시/선택만
