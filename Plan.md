# Plan: 생산 대기열 FIFO 기준을 승인(PRODUCTION 진입) 시각으로 변경

> 관련 docs: [docs/05-생산라인조회.md](docs/05-생산라인조회.md) (갱신 완료)

## 목표

생산 라인 대기열 순서를 주문 접수 시각(`created_at`)이 아니라, 실제로 승인되어 `PRODUCTION`으로 전환된 시각 기준 FIFO로 바꾼다. 접수는 먼저 됐지만 승인이 늦어진 주문이, 나중에 접수됐지만 먼저 승인된 주문보다 뒤로 밀리도록 한다.

## 접근 방식

- `Order`에 `production_queued_at: str | None` 필드 추가(`decide()`가 `PRODUCTION`으로 전이시키는 시점에 기록).
- `OrderRepository.set_production_queued_at(order_id, queued_at)` 추가, DB 마이그레이션에 컬럼 추가(레거시 데이터는 `NULL`).
- `advance_production_line()`의 대기열 정렬 키를 `o.created_at` → `o.production_queued_at or o.created_at`(레거시 주문은 큐 진입 시각이 없으니 접수 시각으로 폴백)으로 변경.

## 영향받는 파일

- `app/models.py` — `Order.production_queued_at` 추가
- `app/db.py` — 마이그레이션에 컬럼 추가
- `app/repository.py` — `set_production_queued_at` 추가, `from_row` 갱신
- `app/services.py` — `decide()`가 큐 진입 시각 기록, `advance_production_line()` 정렬 키 변경
- `tests/test_services.py` — FIFO가 승인 시각 기준임을 검증하는 테스트 추가
- `docs/05-생산라인조회.md`, `PRD.md` — 이미/갱신 예정

## 구현 & 검증 방법

- [x] 구현: 위 내용 전부 — 단, 최초 구현(타임스탬프 `production_queued_at`)에서 **실제 버그를 발견**해 설계를 변경함
  - **버그 발견**: 신규 테스트(`test_waiting_queue_orders_by_decision_time_not_receipt_time`)가 실패 — 원인 확인 결과, 이 환경의 시스템 시계 해상도가 낮아 연달아 호출된 `decide()` 두 건이 완전히 동일한 `datetime.now(timezone.utc)` 타임스탬프를 받음(`time.time()` 반복 호출로 재현 확인). 타임스탬프로는 FIFO 순서를 보장할 수 없음.
  - **수정**: `production_queued_at`(타임스탬프)을 `production_queue_seq`(정수, `next_production_queue_seq()`로 현재 최댓값+1 부여)로 교체 — 항상 유일하고 엄격하게 증가하므로 동시성 문제 없음.
  - 확인: 신규 테스트로 "접수는 먼저, 승인은 나중" 주문이 "접수는 나중, 승인은 먼저"인 주문보다 뒤에 생산되는지 확인(수정 후 통과)
  - 확인: `python -m unittest discover tests` 전체 통과(50/50, 신규 3건 — FIFO 검증 1건 + repository `next_production_queue_seq` 2건 — 포함, 회귀 없음)
  - 확인(사람 확인 선행): 실제 프로젝트 db와 분리된 임시 DB로 접수/승인 시각이 어긋나는 시나리오(OA: 2020년 접수·마지막에 승인, OB: 최근 접수·가장 먼저 승인, OC: 중간 접수·두번째 승인) 구성 — 생산 라인 화면의 대기 목록이 실제로 "OC, OA" 순서(승인 순서)로 표시되고 접수 순서(OA가 가장 먼저 접수됐음에도)를 따르지 않음을 raw 출력으로 확인. 실제 프로젝트 DB(108개 주문) 마이그레이션도 데이터 손실 없이 확인.

## 가벼운 자체 점검 (커밋 전, 필수)

- [x] 문서 정합성: docs/05/PRD.md가 실제 구현(정수 순번 방식, 타임스탬프 방식이 왜 안 됐는지 포함)과 일치하도록 갱신
- [x] 범위 준수: 화면/다른 로직 변경 없음(정렬 기준 및 관련 필드만)
- [x] 테스트: 50/50 통과, FIFO 기준 변경 회귀 테스트 포함
- [x] 컨벤션 준수: 큐 정렬/순번 부여 로직은 services.py(`decide`)와 repository.py(`next_production_queue_seq`)에 유지, cli.py는 표시만
