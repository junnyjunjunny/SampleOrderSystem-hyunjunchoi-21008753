# Plan: <기능/수정 이름>

> 이 파일은 템플릿입니다. RED 단계를 시작할 때 이 내용을 `Plan.md`로 복사한 뒤 채워서 사용자 검토를 요청하세요.
> 절차 전체 규칙은 [CLAUDE.md](CLAUDE.md)의 "작업 진행 방식" / "Harness" 섹션 참고.

## 목표

<이 기능/수정이 달성해야 하는 것을 한두 문장으로. 사용자와의 토론 결과를 반영.>

## 접근 방식

<설계 옵션과 선택한 방향, 그 이유. 여러 옵션이 있었다면 왜 이 옵션을 골랐는지.>

## 영향받는 파일

- <파일 경로> — <어떤 변경>
- ...

## RED — 작성할 실패 테스트

- [ ] `tests/test_xxx.py::<테스트명>` — <검증하려는 동작>
- [ ] ...

## GREEN — Action & 검증 방법

각 Action 항목은 "무엇을 구현하는가"뿐 아니라 "어떻게 검증하는가"를 함께 적는다.

- [ ] Action: <구현 내용>
  - Verify (Correctness): `python -m unittest discover tests` 통과 여부로 확인. <구체적으로 어떤 테스트>
  - Verify (사람 확인 선행, 필요 시): <사람이 최종 확인할 항목을 AI가 먼저 재현/검증해서 결과를 남긴다>
  - Verify (Safety Test, 필요 시): `/tmp`에서 비정상/경계값/악의적 입력에 대한 공격적 테스트를 수행하고 결과를 기록한다.

## SubAgent 리뷰 체크리스트 (Test 통과 후, 매 사이클 필수)

- [ ] SubAgent1 `doc-consistency-verifier`: PRD.md/README.md/CLAUDE.md와 구현 정합성 확인
- [ ] SubAgent2 `ai-action-executor`: 이 Plan.md에 명시된 범위대로만 구현됐는지 확인
- [ ] SubAgent3 `test-verify`: 테스트가 실제로 실패→통과했는지, 커버리지 공백 확인
- [ ] SubAgent4 `compliance-verify`: CLAUDE.md 규칙(컨벤션/커밋 규칙 등) 준수 확인

## REVIEW — 사람 최종 확인

- [ ] 위 4개 SubAgent 리뷰 통과
- [ ] 사람이 Plan.md 대비 구현 범위 확인
- [ ] 리팩터링 필요 여부 확인 및 반영
- [ ] 승인 후 Conventional Commits 형식으로 커밋
