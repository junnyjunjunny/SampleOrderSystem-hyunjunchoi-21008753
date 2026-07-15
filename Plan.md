# Plan: 시료 관리 목록에 생산시간 컬럼 추가 + 검증용 초단위 생산시간 조정

> 관련 docs: [docs/01-시료관리.md](docs/01-시료관리.md) (갱신 완료)

## 목표

1. `[1] 시료 관리` 목록/검색 표에 평균 생산시간 컬럼을 추가한다.
2. `scripts/seed_samples.py`의 `avg_production_time`을 시료별로 조금씩 다르게, 사람이 기다리며 검증할 수 있는 수준(약 0.06~0.25 sec/ea)으로 크게 줄인다.
3. 이미 시딩되어 있는 실제 프로젝트 DB의 23개 시료에도 새 값을 반영한다(스크립트는 신규 삽입만 하므로 별도 업데이트 필요).

## 접근 방식

- `print_sample_table`에 "생산시간(sec/ea)" 컬럼 추가 — 저장은 `min/ea`지만 값이 매우 작아지므로 표시는 `avg_production_time * 60`(초 환산)으로 보여준다.
- `scripts/seed_samples.py`의 `SAMPLES` 목록에서 `avg_production_time`만 시료별로 다른 초소형 값(분 단위, 0.0010~0.0042)으로 교체. 이름/수율/재고는 그대로 유지.
- 실제 `samples.db`는 이미 23개 시료가 존재해 `seed_samples.py` 재실행으로는 갱신되지 않으므로(생성만 하고 중복은 건너뜀), `SampleRepository.update()`로 새 `avg_production_time` 값만 직접 반영(이름/수율/재고 값은 유지).

## 영향받는 파일

- `app/cli.py` — `print_sample_table` 컬럼 추가
- `scripts/seed_samples.py` — `avg_production_time` 값 교체
- `docs/01-시료관리.md` — 이미 갱신됨
- 실제 프로젝트 `samples.db`의 기존 23개 시료 — `avg_production_time`만 일괄 갱신(1회성 데이터 동기화, 코드 변경 아님)

## 구현 & 검증 방법

- [x] 구현: `print_sample_table` 컬럼 추가
  - 확인: `python -m unittest discover tests` 전체 통과(47/47, 순수 표시 로직이라 회귀 없음)
  - 확인(사람 확인 선행): 실제 `main.py`로 `[1] 시료 관리` 진입해 "생산시간(sec/ea)" 컬럼과 값(예: S-001 0.10)이 정확히 표시되는지 확인
- [x] 구현: `seed_samples.py` 값 교체 + 실제 DB 23개 시료 `avg_production_time` 동기화
  - 확인: 실제 DB에서 23개 시료 전부 `updated=23, missing=0`으로 갱신 확인, 몇 개 샘플 값 직접 조회로 확인(이름/수율/재고는 변경 없음)

## 가벼운 자체 점검 (커밋 전, 필수)

- [x] 문서 정합성: docs/01-시료관리.md이 실제 구현과 일치
- [x] 범위 준수: 다른 화면/서비스 로직 변경 없음
- [x] 테스트: 47/47 통과, 회귀 없음
- [x] 컨벤션 준수: 표시 전용 변환(초 환산)이라 cli.py에만 위치, 저장 단위(min/ea)는 그대로 유지
