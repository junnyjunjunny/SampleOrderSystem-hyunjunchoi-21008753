# Plan: 시료 관리 UX — 화면 clear, 페이지네이션, 수정/삭제 하위 메뉴

> 이전 사이클(등록 값 검증 + 검색, 이미 REVIEW 완료·미커밋)에 이어서 진행. 두 사이클은 한 번에 묶어서 커밋한다.
> `docs/01-시료관리.md` 갱신 내용을 기준으로 한다. 절차는 [CLAUDE.md](CLAUDE.md) 참고.

## 목표

1. `main.py` 실행 및 각 메뉴 진입 시 화면을 지워(`cls`) 이전 내용 없이 깔끔하게 보이도록 한다.
2. `[1] 시료 관리` 진입 시 등록된 시료 목록을 5개씩 페이지네이션(`N`/`B`)으로 보여준다.
3. 시료 관리 하위 메뉴(`1` 검색, `2` 등록, `3` 수정/삭제, `0` 뒤로)를 구성한다.

## 접근 방식

- **화면 clear**: `app/cli.py`에 `clear_screen()` 추가(`os.system("cls")`, Windows 전용으로 확정). `run()`의 메인 루프 최상단과, 신설되는 `sample_management_menu()` 루프 최상단에서 호출한다.
- **액션 후 대기**: 각 액션(등록/검색/수정/삭제 등) 실행 직후 결과를 보여준 채로 `input("계속하려면 Enter > ")`로 대기한 뒤 화면을 지우고 목록/메뉴를 다시 그린다. 결과가 보자마자 지워지는 것을 방지.
- **페이지네이션**: 순수 함수 `paginate(items, page, page_size=5) -> (page_items, page, total_pages)`를 `app/cli.py`에 추가하고, 콘솔 입출력과 분리해 유닛 테스트한다(`tests/test_cli.py` 신규). 페이지는 유효 범위로 클램프한다.
- **시료 관리 하위 메뉴**: `sample_management_menu(sample_repo)` 함수를 신설해 메인 메뉴 `[1]`이 여기로 진입하도록 바꾼다. 기존 `register_sample`, `search_samples`는 그대로 재사용하고, 신규 `edit_or_delete_sample(sample_repo)`를 추가한다.
- **수정/삭제**: `SampleRepository`에 `update(sample: Sample)`(전체 필드 덮어쓰기, `sample_id`는 키로만 사용)와 `delete(sample_id)`를 추가한다. 수정 시 새 `Sample`을 생성해 `__post_init__` 검증을 재사용한다.
- **예외 처리 컨벤션 일반화**: 지금까지 CLAUDE.md는 "cli.py의 최상위 루프에서만 캐치"라고 되어 있었는데, 이제 `run()`과 `sample_management_menu()` 두 개의 루프가 생긴다. "각 메뉴 자신의 루프 최상위에서 캐치"로 문구를 일반화한다.
- **메인 메뉴 재구성**: 기존 `[1] 시료 등록`, `[2] 시료 조회`, `[9] 시료 검색`을 제거하고 `[1] 시료 관리`로 통합한다. 나머지(주문 접수/승인/거절/생산시작/출고/주문목록)는 이번 사이클 범위 밖이라 번호만 당겨서 유지한다(`[2]~[7]`). 6개 메인 메뉴로의 전체 재편(모니터링/생산라인조회 포함)은 여전히 범위 밖(`docs/05-생산라인조회.md` TODO 참고).

## 영향받는 파일

- `app/cli.py` — `clear_screen`, `paginate`, `sample_management_menu`, `edit_or_delete_sample` 추가, 메인 메뉴 재구성
- `app/repository.py` — `SampleRepository.update`, `SampleRepository.delete` 추가
- `tests/test_repository.py` — update/delete 테스트 추가
- `tests/test_cli.py` — 신규 파일, `paginate` 순수 함수 테스트
- `docs/01-시료관리.md` — 이미 갱신됨
- `CLAUDE.md` — 예외 처리 컨벤션 문구 일반화, UX 컨벤션(화면 clear/페이지네이션) 한 줄 추가

## RED — 작성할 실패 테스트

- [x] `tests/test_repository.py::SampleRepositoryTest::test_update_modifies_fields_except_id`
- [x] `tests/test_repository.py::SampleRepositoryTest::test_update_missing_raises_key_error`
- [x] `tests/test_repository.py::SampleRepositoryTest::test_delete_removes_sample`
- [x] `tests/test_repository.py::SampleRepositoryTest::test_delete_missing_raises_key_error`
- [x] `tests/test_cli.py::PaginateTest::test_first_page_by_default`
- [x] `tests/test_cli.py::PaginateTest::test_computes_total_pages`
- [x] `tests/test_cli.py::PaginateTest::test_clamps_page_within_valid_range`
- [x] `tests/test_cli.py::PaginateTest::test_empty_items_returns_single_page`

## GREEN — Action & 검증 방법

- [x] Action: `SampleRepository.update`/`delete` 구현
  - Verify (Correctness): 위 4개 repository RED 테스트 통과 완료
- [x] Action: `paginate` 순수 함수 구현
  - Verify (Correctness): 위 4개 cli RED 테스트 통과 완료
- [x] Action: `clear_screen`, `sample_management_menu`, `edit_or_delete_sample` 구현 및 메인 메뉴 재구성
  - Verify (Correctness): `python -m unittest discover tests` 전체 통과(30/30, 회귀 없음)
  - Verify (사람 확인 선행): 임시 DB로 `cli.run()`을 직접 구동해 6건 등록 후 목록이 5+1로 페이지네이션되고 `N`으로 2페이지 이동, 마지막 페이지에서 `N`은 "마지막 페이지입니다" 안내 후 이동하지 않는 것 확인. `[3] 수정/삭제`로 일부 필드만 새 값 입력하고 나머지는 엔터로 유지 → 지정한 필드만 반영되는 것 확인(재고 999로 변경, 이름/생산시간/수율 유지). 검증 중 실수로 프로젝트 루트 `samples.db`에 기록되어 정리(gitignore 대상, 삭제 완료).

## SubAgent 리뷰 체크리스트 (Test 통과 후, 매 사이클 필수)

- [x] SubAgent1 `doc-consistency-verifier`: **문제 발견** — `docs/01-시료관리.md`가 "구현 예정"으로 남아있음, `PRD.md`/`README.md` 기능 목록 미반영 → 세 문서 모두 갱신으로 해결
- [x] SubAgent2 `ai-action-executor`: PASS — Plan.md 범위 밖 변경 없음, RED 테스트 8개 전부 일치
- [x] SubAgent3 `test-verify`: 30/30 통과. `edit_or_delete_sample`/`sample_management_menu`의 콘솔 분기 자동 테스트 공백 발견 → 다음 사이클로 이월(TODO로 docs에 기록)
- [x] SubAgent4 `compliance-verify`: **FAIL** — `edit_or_delete_sample`의 `else` 분기가 `ValueError`를 던지지 않고 자체 print+return 처리 → `raise ValueError(...)`로 수정, `sample_management_menu`의 try/except가 캐치하도록 통일

## REVIEW — 사람 최종 확인

- [x] 위 4개 SubAgent 리뷰 통과 (지적 사항 전부 반영 완료, 재테스트 30/30 통과)
- [ ] 사용자가 `py main.py`로 직접 검증
- [ ] 리팩터링 필요 여부 확인 및 반영
- [ ] 승인 후 이전 사이클과 함께 Conventional Commits로 커밋
