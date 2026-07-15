# SampleOrderSystem-hyunjunchoi-21008753

반도체 시료 생산주문관리 시스템 (개인과제 - 미션2: 프로젝트 개발)

## 개요
가상의 반도체 회사 "S-Semi"의 시료(Sample) 생산 주문을 관리하는 콘솔 기반 시스템입니다.
고객의 시료 주문 접수부터 승인/거절, 생산, 출고까지의 전체 흐름을 관리합니다.

## 주요 기능
- 시료 관리 (등록 / 조회 / 검색)
- 시료 주문 (접수)
- 주문 승인 / 거절
- 모니터링 (주문량 / 재고량)
- 생산 라인 조회
- 출고 처리

## 문서
- 요구사항/도메인 설계: [PRD.md](PRD.md)
- 개발 컨벤션(Claude Code 운영 하네스): [CLAUDE.md](CLAUDE.md)

## 구조
```
app/
  db.py          # SQLite 연결 및 스키마 초기화 (samples, orders)
  models.py      # Sample, Order 데이터클래스
  repository.py  # SampleRepository, OrderRepository: Create/Read/Update/Delete
  services.py    # OrderService: 주문 상태 전이 및 재고 검증 규칙
  cli.py         # 콘솔 메뉴 / 입출력
main.py          # 진입점
tests/           # in-memory sqlite 기반 단위 테스트
```

## 실행 방법
```
python main.py
```

## 테스트
```
python -m unittest discover tests
```

## 담당자
- 이름: hyunjunchoi
- 사번: 21008753
