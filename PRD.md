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
- 3번(주문 승인/거절) 메뉴에서 승인(`Y`)을 선택하면, 그 시점의 재고와 주문 수량을 비교해 자동으로 갈린다: 재고가 충분하면 `CONFIRMED`, 부족하면 `PRODUCTION`. 거절(`N`)은 바로 `REJECTED`.
- `PRODUCTION`은 향후 5번(생산 라인 조회) 메뉴가 담당할 자동 생산 로직으로 `CONFIRMED`로 전이하고, 그때 부족했던 만큼 재고를 채운다(`stock += quantity`). 시료의 `avg_production_time`에 따라 시간이 지나면 자동으로 생산되는 방식으로 설계 예정(`docs/05-생산라인조회.md` 참고, 아직 미구현). `OrderService.complete_production`는 이 로직의 기반이 될 API로 이미 존재한다.
- `CONFIRMED`에서 6번(출고 처리) 메뉴로 `RELEASE`로 전이할 때 재고를 주문 수량만큼 차감한다.

## 기능 범위

### 이번 스캐폴드에서 구현 (핵심 흐름)
- 시료 등록 / 조회 / 검색(ID·이름 대소문자 무시 부분일치) / 수정 / 삭제
- 시료 주문 접수
- 주문 승인 / 거절(재고에 따라 `CONFIRMED`/`PRODUCTION` 자동 분기)
- 모니터링(주문량 확인) / 출고 처리

### 다음 단계로 미룸
- 모니터링 재고량 확인 등 추가 하위 메뉴
- 더미 데이터 자동 시딩 — DummyDataGenerator PoC 연계
- 생산 라인 조회 — `PRODUCTION` 주문의 자동 생산 진행 상황 조회 및 완료 처리(시료 `avg_production_time` 기반 시간 경과 자동화)

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
