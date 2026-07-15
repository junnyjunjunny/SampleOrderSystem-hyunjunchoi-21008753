# Plan: 재고 모니터링 로직을 "주문대비"로 변경 + 잔여율(%) 제거

## 목표

`[4] 모니터링 → [2] 재고량 확인`의 여유/부족/고갈 판정을, 기존의 고정 용량(1000) 기반 퍼센트 임계값 대신
PDF 스펙(18p)의 "주문대비" 재고 비교로 바꾼다. "고갈"은 비율이 아니라 재고가 정확히 0인 경우로 판정한다.
잔여율(%) 표시는 기준(분모)이 불명확하므로 화면에서 완전히 제거한다.

## 접근 방식

- "주문대비"의 기준(분모)은 해당 시료를 참조하는 **미해결 주문 수량 합계**로 정의한다: 상태가 `RESERVED` 또는 `PRODUCING`인 주문의 `quantity` 합(= 아직 출고/거절되지 않고 재고에 부담을 주는 진행 중 수요).
- 판정 규칙(우선순위 순):
  1. 재고 == 0 → `고갈`
  2. 재고 >= 미해결 주문 수량 합 → `여유`
  3. 그 외(0 < 재고 < 미해결 주문 수량 합) → `부족`
- 비즈니스 규칙(무엇을 "수요"로 볼지, 여유/부족/고갈 판정)은 컨벤션에 따라 `services.py`에 둔다: `OrderService.pending_order_quantity(sample_id)`(RESERVED+PRODUCING 수량 합)와 모듈 함수 `stock_status(stock, pending_quantity)`(판정 로직)를 추가한다.
- `cli.py`의 `check_stock_level`은 표시만 담당하도록 수정: 시료마다 `service.pending_order_quantity(...)` → `stock_status(...)`을 호출해 라벨/색상만 결정한다. 잔여율(%) 컬럼과 계산은 제거한다.
- 기존 `STOCK_FULL_CAPACITY`/`STOCK_ABUNDANT_THRESHOLD`/`STOCK_LOW_THRESHOLD` 상수와 `_stock_ratio_status` 함수는 삭제한다(더 이상 쓰이지 않음).

## 영향받는 파일

- `app/services.py` — `OrderService.pending_order_quantity` 추가, 모듈 함수 `stock_status` 추가
- `app/cli.py` — `check_stock_level` 시그니처에 `OrderService` 추가(호출부 `monitoring_menu`도 함께 수정), `_stock_ratio_status`/관련 상수 제거, 잔여율 컬럼 제거
- `tests/test_services.py` — `pending_order_quantity`/`stock_status`에 대한 정상/경계 케이스 테스트 추가
- `docs/04-모니터링.md`, `PRD.md`(필요 시) — 재고량 확인 로직 서술 갱신

## docs/ 갱신 대상

- `docs/04-모니터링.md` — `[2] 재고량 확인`의 컬럼(잔여율 제거), 판정 로직(주문대비 + 고갈=0)로 갱신

## 구현 & 검증 방법

- [ ] 구현: `services.py`에 `pending_order_quantity`/`stock_status` 추가
  - 확인: 새 테스트(재고>미해결수요→여유, 0<재고<미해결수요→부족, 재고=0→고갈(미해결수요가 0이어도 고갈), 미해결수요=0이고 재고>0→여유)로 `python -m unittest discover tests` 통과
- [ ] 구현: `cli.py`의 `check_stock_level`을 새 로직으로 교체, 잔여율 컬럼/상수/구함수 제거
  - 확인(사람 확인 선행): 임시 DB로 시료 3개(재고 0/부족/충분) + 각각에 대한 RESERVED·PRODUCING 주문을 만들어 재고량 확인 화면에 고갈/부족/여유가 정확히 표시되고 잔여율 컬럼이 없는지 확인

## 가벼운 자체 점검 (커밋 전, 필수)

- [ ] 문서 정합성: docs/04-모니터링.md, PRD.md가 실제 구현과 일치
- [ ] 범위 준수: 다른 메뉴/로직 변경 없음(1번 상태명 변경 건과 무관)
- [ ] 테스트: 전체 통과, 새 로직에 대한 경계 케이스 포함
- [ ] 컨벤션 준수: 비즈니스 규칙(수요 계산, 여유/부족/고갈 판정)은 services.py에, cli.py는 표시만
