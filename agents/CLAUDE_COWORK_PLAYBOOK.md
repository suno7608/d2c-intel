# Claude Code / Claude Co-work 활용 플레이북

## 목적
Codex가 작성한 주간 인텔리전스 초안을 Claude가 2차 검증해,
- 근거 누락
- 과장/비약
- 액션 아이템 실행력 부족
을 줄인다.

## 역할 분담
1. OpenClaw: 다국가 신호 수집
2. Codex: 구조화 + 초안 작성
3. Claude Co-work: 품질 게이트(반론/검증/문장 보정)

## 운영 모드
### Mode A: 자동 Co-work (권장)
- `CLAUDE_RUNNER`를 `agents/claude_runner_cli.sh`로 설정
- `scripts/run_weekly.sh` 실행 시 자동 검토
- 실패하면 자동 fallback(copy)

### Mode B: 수동 Co-work
- `prompts/claude_cowork_review.md` + 초안 Markdown을 Claude Code에 직접 전달
- 수정본을 `_claude.md`로 저장
- QA 파일(`qa/qa_summary_*.md`)에 주요 변경점을 기록

## 품질 게이트 체크리스트
- [ ] 모든 수치/인용/사실에 URL 있음
- [ ] URL 없으면 `❓[출처 미확인 — 검색어: "..."]`
- [ ] Executive Summary 액션에 Owner/Deadline 있음
- [ ] Critical Alert는 국가/제품/영향도 포함
- [ ] 한국어 서술 + 영문 고유명사 보존 규칙 준수

## 권장 프롬프트 체인
1. "증거 없는 단정 문장만 찾아줘"
2. "링크 포맷 위반만 찾아줘"
3. "P1/P2/P3 실행 가능성 기준으로 액션 재작성"
4. "최종본 Markdown만 출력"

## 주의사항
- Claude CLI가 응답 지연/실패 시 timeout 후 fallback 처리됨
- 자동 단계에서 모델 출력이 구조화 JSON이 아닐 수 있으므로 QA 로그를 반드시 확인
