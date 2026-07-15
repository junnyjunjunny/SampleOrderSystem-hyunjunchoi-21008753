# Plan: 주문 승인/거절(3번) 재구현 — 상태 모델 변경(CONFIRMED/PRODUCTION), 번호 선택형 목록

> 관련 docs: [docs/03-주문승인거절.md](docs/03-주문승인거절.md), [docs/06-출고처리.md](docs/06-출고처리.md), [docs/05-생산라인조회.md](docs/05-생산라인조회.md), [PRD.md](PRD.md) (모두 갱신 완료)

## 목표

1. 메인 메뉴 `[3] 주문 승인`/`[4] 주문 거절`을 `[3] 주문 승인/거절` 하나로 합친다.
2. `[3]` 진입 시 `RECEIVED` 목록을 번호/주문번호/고객/시료/수량/상태 컬럼으로 페이지네이션 표시한다.
3. 번호를 입력하면 시료/현재재고/주문수량/부족분(재고-수량, 음수면 빨간 글씨)을 보여주고 `[Y]승인 [N]거절`을 받는다.
4. 승인 시 재고 비교로 `CONFIRMED`(충분)/`PRODUCTION`(부족)으로 자동 분기, 거절 시 `REJECTED`.
5. 결정된 주문은 목록에서 사라진다(더 이상 RECEIVED가 아니므로).
6. `PRODUCTION`은 메인 메뉴 `[4] 생산 완료`(기존 "생산 시작" 자리 재활용)에서 완료 처리하면 `CONFIRMED`로 바뀌고, 그만큼 재고가 채워진다(`stock += quantity`).
7. `[5] 출고`는 이제 `CONFIRMED → SHIPPED`를 처리(기존 `IN_PRODUCTION → SHIPPED`에서 변경).

## 접근 방식

- **상태 상수 교체**: `app/models.py`에서 `APPROVED`/`IN_PRODUCTION` 제거, `CONFIRMED`/`PRODUCTION` 추가.
- **서비스 계층**: `ALLOWED_TRANSITIONS`를 `RECEIVED: {CONFIRMED, PRODUCTION, REJECTED}`, `PRODUCTION: {CONFIRMED}`, `CONFIRMED: {SHIPPED}`로 교체.
  - `OrderService.decide(order_id, approve: bool) -> str`: 거절이면 `REJECTED`; 승인이면 재고 비교 후 `CONFIRMED`/`PRODUCTION` 중 하나로 전이하고 결과 상태를 반환(기존 `approve`/`reject` 대체).
  - `OrderService.complete_production(order_id)`: `PRODUCTION → CONFIRMED` 전이 + `stock += quantity` (기존 `start_production` 대체).
  - `ship`은 그대로 두되 `ALLOWED_TRANSITIONS` 변경으로 자연히 `CONFIRMED` 전제가 됨.
- **CLI**: 메인 메뉴를 `[1]시료관리 [2]시료주문 [3]주문승인/거절 [4]생산완료 [5]출고 [6]주문목록 [0]종료`로 재구성.
  - `order_approval_menu(sample_repo, order_repo, service)`: 시료관리와 동일한 clear+페이지네이션 패턴. 표에 1부터 시작하는 번호 컬럼을 붙이고, 번호 입력 시 해당 주문의 부족분(빨간 글�스 ANSI, 음수일 때만)을 보여준 뒤 `[Y]/[N]` 선택.
  - `complete_production_order(service)`: 주문번호를 입력받아 `service.complete_production` 호출(기존 `start_production` cli 함수 대체).
  - 기존 `approve_order`/`reject_order`/`start_production` cli 함수는 삭제.
- **ANSI 색상**: Windows 콘솔에서 이스케이프가 먹히도록 `clear_screen()`에서 `os.system("cls")` 다음에 `os.system("")`을 한 번 더 호출해 VT100 처리를 활성화한다.

## 영향받는 파일

- `app/models.py` — `CONFIRMED`/`PRODUCTION` 상수 교체
- `app/services.py` — `ALLOWED_TRANSITIONS`, `decide`, `complete_production` (기존 `approve`/`reject`/`start_production` 대체)
- `app/cli.py` — `order_approval_menu`, `complete_production_order` 신설, 기존 `approve_order`/`reject_order`/`start_production` 삭제, 메인 메뉴 재구성, `clear_screen`에 ANSI 활성화 추가
- `tests/test_services.py` — 기존 승인/거절/생산시작 테스트를 `decide`/`complete_production` 기준으로 갱신
- `docs/03`, `docs/05`, `docs/06`, `PRD.md` — 이미 갱신됨

## 구현 & 검증 방법

- [x] 구현: 모델/서비스 계층 교체(`decide`, `complete_production`, `ALLOWED_TRANSITIONS`)
  - 확인: `tests/test_services.py` 갱신 후 전체 통과 (42/42)
  - **버그 발견 및 수정**: `_transition`만으로는 `RECEIVED→CONFIRMED`(decide)와 `PRODUCTION→CONFIRMED`(complete_production)를 구분 못해, `complete_production`을 `RECEIVED` 주문에도, `decide`를 이미 `PRODUCTION`인 주문에도 잘못 적용할 수 있었음 → 두 메서드에 명시적 전제 상태 검사 추가, 회귀 테스트(`test_complete_production_without_production_status_raises`, `test_decide_on_production_order_raises`) 추가로 커버
- [x] 구현: `cli.py`(`order_approval_menu`, `complete_production_order`, 메인 메뉴 재구성, ANSI 활성화)
  - 확인: `python -m unittest discover tests` 전체 통과(42/42, 회귀 없음)
  - 확인(사람 확인 선행): 실제 프로젝트 db와 분리된 임시 DB로 `cli.run()` 구동 — 재고충분 주문 승인→CONFIRMED, 재고부족 주문 승인→PRODUCTION(부족분 `-45`가 ANSI 빨간색 코드로 출력됨), 거절→REJECTED, 결정 후 목록에서 사라짐 확인. `[4] 생산 완료`로 PRODUCTION→CONFIRMED 전이 및 재고 5→55(+50) 보충 확인. `[5] 출고`로 CONFIRMED→SHIPPED 전이 및 재고 55→52(-3) 차감 확인. 실제 프로젝트 `samples.db`(사용자의 기존 주문 001~008 포함)는 전혀 건드리지 않음.
  - **버그 발견 및 수정**: PRODUCTION 안내 메시지에 em-dash(`—`)가 포함되어 있어 Windows 콘솔(cp949)에서 `UnicodeEncodeError`로 크래시함 → 일반 콜론으로 교체, 전체 `cli.py`를 스캔해 다른 cp949 비호환 문자 없음을 확인

## 가벼운 자체 점검 (커밋 전, 필수)

- [x] 문서 정합성: PRD.md/docs/03/docs/05/docs/06이 실제 구현과 일치하도록 갱신
- [x] 범위 준수: 이 Plan.md에 없는 변경 없음(모니터링/생산라인조회 등은 손대지 않음)
- [x] 테스트: 42/42 통과, 새 상태 전이마다 실패 케이스 포함 + 자체 점검 중 발견한 2개 버그의 회귀 테스트 추가
- [x] 컨벤션 준수: 재고 비교/상태 분기 로직이 `services.py`(`decide`, `complete_production`)에 있고 `cli.py`는 입출력/표시만 담당

## 추가 반영 (사용자 피드백)

- [x] 번호 선택 후 `[Y]승인 [N]거절` 화면에 `[0] 뒤로`를 추가해 아무 결정도 안 하고 목록으로 돌아갈 수 있게 함. 취소 시에는 상태 변화가 없고 "계속하려면 Enter" 대기도 건너뛴다(`decide_selected_order`가 `bool`을 반환해 `order_approval_menu`가 pause 여부를 결정). 격리된 임시 DB로 재현 확인, 테스트 42/42 유지.
