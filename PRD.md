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
RECEIVED --승인--> APPROVED --생산 시작--> IN_PRODUCTION --출고--> SHIPPED
   |
   --거절--> REJECTED
```

- 상태 전이는 `OrderService`가 검증한다(허용되지 않는 전이는 `ValueError`).
- `APPROVED`로 전이할 때 재고(`stock`)가 주문 수량 이상인지 확인한다.
- `SHIPPED`로 전이할 때 재고를 주문 수량만큼 차감한다.

## 기능 범위

### 이번 스캐폴드에서 구현 (핵심 흐름)
- 시료 등록 / 조회 / 검색(ID·이름 대소문자 무시 부분일치) / 수정 / 삭제
- 시료 주문 접수
- 주문 승인 / 거절
- 생산 시작 / 출고 처리
- 주문 목록 조회(상태별 필터링)

### 다음 단계로 미룸
- 모니터링 대시보드(주문량/재고량 실시간 집계) — DataMonitor PoC 연계
- 더미 데이터 자동 시딩 — DummyDataGenerator PoC 연계
- 생산 라인 조회(라인별 배정)

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
