# PRD - SampleOrderSystem

반도체 시료 생산주문관리 시스템 "S-Semi" 콘솔 애플리케이션의 제품 요구사항 정의.

## 배경

4개의 PoC(ConsoleMVC, DataPersistence, DataMonitor, DummyDataGenerator)에서 검증한 요소를 통합하여,
시료 주문의 접수부터 출고까지 전체 흐름을 관리하는 콘솔 애플리케이션을 완성한다.

## 도메인 모델

### Sample (시료)
| 필드 | 타입 | 설명 | 제약 |
|---|---|---|---|
| sample_id | str | PK | 필수, 중복 불가 |
| name | str | 시료명 | 필수 |
| avg_production_time | float | 평균 생산시간(분/개) | 0보다 커야 함 |
| yield_rate | float | 수율 (0~1) | 0 이상 1 이하 |
| stock | int | 현재 재고 | 0 이상 |

값 검증은 `Sample.__post_init__`(생성 시점)에서 수행하며, 위반 시 `ValueError`를 던진다.

### Order (주문)
| 필드 | 타입 | 설명 |
|---|---|---|
| order_id | str | PK |
| sample_id | str | FK -> Sample |
| customer_name | str | 고객명 |
| quantity | int | 주문 수량 |
| status | str | 주문 상태 |
| created_at | str | 접수 시각(ISO) |
| production_quantity | int, nullable | 실 생산량(`ceil(부족분/수율)`). `PRODUCTION` 전이 시 결정 |
| production_started_at | str, nullable | 생산 라인에서 "현재 처리 중"이 된 시각(ISO, UTC). 단일 생산 라인이라 한 번에 하나의 주문만 값을 가짐 |
| production_queue_seq | int, nullable | 생산 대기열 진입 순번(FIFO 정렬 기준). `PRODUCTION` 전이 시 부여, 접수 시각이 아니라 승인 시각 기준으로 순서를 매김 |

### 주문 상태 흐름

```
RECEIVED --승인(재고 충분)--> CONFIRMED --출고--> RELEASE
   |         승인(재고 부족)
   |              v
   |         PRODUCTION --생산 완료--> CONFIRMED
   |
   --거절--> REJECTED
```

- 상태 전이는 `OrderService`가 검증한다(허용되지 않는 전이는 `ValueError`).
- 시료 주문(2번) 메뉴는 접수만 담당하며 접수된 주문은 `RECEIVED`로 저장되고 끝난다. 승인/거절 판단은 전적으로 3번 메뉴에서 이후에 진행한다.
- 3번(주문 승인/거절) 메뉴에서 승인(`Y`)을 선택하면, 그 시점의 재고와 주문 수량을 비교해 자동으로 갈린다: 재고가 충분하면 `CONFIRMED`로 전이하며 **그 즉시 `stock -= quantity`**, 부족하면 `PRODUCTION`으로 전이(재고는 이 시점엔 변화 없음). 거절(`N`)은 바로 `REJECTED`.
- `PRODUCTION`은 5번(생산 라인 조회) 화면 진입마다 실행되는 `OrderService.advance_production_line()`이 시간 경과에 따라 자동으로 `CONFIRMED`로 전이시키고, 그때 `stock += production_quantity - quantity`로 재고를 정산한다(부족분 보충과 이 주문 소비분 차감을 함께 반영). 생산 라인은 1개(단일 라인)라 한 번에 하나의 주문만 처리되며, 나머지는 승인 시각 기준 FIFO로 대기열에서 순서를 기다린다. 자세한 계산식은 `docs/05-생산라인조회.md` 참고.
- **재고 차감은 항상 `CONFIRMED`가 되는 시점(승인 즉시 또는 생산 완료 시)에 끝난다.** 6번(출고 처리) 메뉴는 `CONFIRMED → RELEASE` 상태 전이만 할 뿐 재고를 건드리지 않는다.

## 기능 범위

### 이번 스캐폴드에서 구현 (핵심 흐름)
- 시료 등록 / 조회 / 검색(ID·이름 대소문자 무시 부분일치) / 수정 / 삭제
- 시료 주문 접수
- 주문 승인 / 거절(재고에 따라 `CONFIRMED`/`PRODUCTION` 자동 분기)
- 모니터링(주문량/재고량 확인) / 생산 라인 조회(자동 생산 진행) / 출고 처리

### 다음 단계로 미룸
- 더미 데이터 자동 시딩 — DummyDataGenerator PoC 연계

## 아키텍처

`repository`(데이터 접근) + `service`(상태 전이/비즈니스 규칙) + `cli`(콘솔 입출력) 3계층으로 구성한다.
DataPersistence PoC의 `db.py`/`models.py`/`repository.py` 패턴을 그대로 확장하고,
ConsoleMVC PoC의 controller 책임(사용자 입력 처리)은 `cli.py`가 대신한다.

## 저장 방식

SQLite(`samples.db`), 프로젝트 루트에 자동 생성. `samples`, `orders` 두 테이블 사용.

## 테스트

`unittest` + in-memory sqlite. repository CRUD와 service의 상태 전이 규칙을 각각 검증한다.

## 담당자
- 이름: hyunjunchoi
- 사번: 21008753
