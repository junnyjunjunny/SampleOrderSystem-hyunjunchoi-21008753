# Plan: 시료 주문(2번) 단순화 — 목록 제거, 접수 즉시 승인/거절

> 이전 사이클(FORWARDED 상태 도입, RECEIVED 목록+페이지네이션)을 되돌리는 정정. `docs/02-시료주문.md`/`docs/03-주문승인거절.md`/`PRD.md` 갱신 완료.

## 목표

1. `[2] 시료 주문`에서 RECEIVED 목록/페이지네이션을 제거한다.
2. 진입 시 바로 `[1] 주문 접수  [0] 뒤로` 두 옵션만 보여준다.
3. 주문 접수(시료ID/고객명/수량 입력) 직후, 그 자리에서 바로 승인/거절을 선택해 반영한다.
4. `FORWARDED` 상태와 관련 코드(서비스/모델/테스트)를 전부 제거하고 `RECEIVED → {APPROVED, REJECTED}`로 되돌린다.

## 접근 방식

- **상태 되돌리기**: `app/models.py`에서 `FORWARDED` 제거. `app/services.py`의 `ALLOWED_TRANSITIONS`를 `RECEIVED: {APPROVED, REJECTED}`로 되돌리고 `OrderService.forward` 삭제.
- **UI 교체**: `app/cli.py`의 `order_management_menu`/`print_order_table`/`forward_order`를 제거하고, 대신 `order_reception_menu(sample_repo, order_repo, service)` + `receive_and_decide(sample_repo, order_repo, service)`를 신설.
  - `order_reception_menu`: `[1] 주문 접수  [0] 뒤로`만 있는 단순 루프(목록 없음).
  - `receive_and_decide`: 시료ID/고객명/수량 입력 → `service.receive_order(...)` → 시료명/재고/주문수량 표시 → `[1] 승인  [2] 거절]` 입력 → `service.approve`/`reject` 호출.
- **기존 3번 메뉴 유지**: 메인 메뉴 `[3] 주문 승인`/`[4] 주문 거절`(`approve_order`/`reject_order`)은 그대로 둔다 — 접수 시 재고 부족 등으로 바로 처리 못한 `RECEIVED` 주문을 나중에 처리하는 용도로 계속 동작.
- **주문번호 자동 생성은 유지**: `OrderRepository.next_order_id`는 그대로 사용(이 기능 자체는 이번 요청과 무관하게 계속 필요).
- **테스트**: `FORWARDED` 관련 테스트(`test_forward_*`, `test_approve_without_forwarding_raises`) 삭제하고 `OrderServiceTest.setUp`을 원래대로(`RECEIVED` 상태로 즉시 승인/거절 가능) 되돌린다. `next_order_id`/`receive_order` 테스트는 유지.

## 영향받는 파일

- `app/models.py` — `FORWARDED` 제거
- `app/services.py` — `ALLOWED_TRANSITIONS` 되돌리기, `forward` 삭제
- `app/cli.py` — `order_management_menu`/`print_order_table`/`forward_order` 삭제, `order_reception_menu`/`receive_and_decide` 신설, 메인 메뉴 `[2]` 연결 변경
- `tests/test_services.py` — FORWARDED 관련 테스트 삭제, 기존 픽스처 원복
- `docs/02-시료주문.md`, `docs/03-주문승인거절.md`, `PRD.md` — 이미 갱신됨

## 구현 & 검증 방법

- [x] 구현: 모델/서비스에서 `FORWARDED` 제거, 테스트 원복
  - 확인: `python -m unittest discover tests` 전체 통과 (36/36)
- [x] 구현: `cli.py`의 `order_reception_menu`/`receive_and_decide`로 교체
  - 확인(사람 확인 선행): 실제 `cli.run()` 구동 — `[2]` 진입 시 목록 없이 `[1]주문접수 [0]뒤로`만 보임, 접수(`O-20260715-007`) 직후 시료명/재고/수량 표시 후 `[1]승인 [2]거절` 선택이 즉시 반영되어 상태가 `APPROVED`로 확인됨. 검증용 주문은 정리, 사용자가 직접 만든 `O-20260715-006`은 그대로 둠.

## 가벼운 자체 점검 (커밋 전, 필수)

- [x] 문서 정합성: PRD.md/docs/02/docs/03이 실제 구현과 일치하도록 갱신
- [x] 범위 준수: 3번/4번 메인 메뉴(`approve_order`/`reject_order`) 코드 자체는 변경 없음, 문서만 두 진입 경로를 설명하도록 보강
- [x] 테스트: 36/36 통과, FORWARDED 관련 코드/테스트 완전히 제거됨
- [x] 컨벤션 준수: `receive_and_decide`는 입력 수집 후 `service.receive_order`/`approve`/`reject`만 호출 — 비즈니스 로직은 여전히 `services.py`에 위치
