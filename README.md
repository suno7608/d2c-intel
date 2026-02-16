# Global D2C Weekly Intelligence Pipeline (OpenClaw + Codex + Claude)

이 프로젝트는 LG 글로벌 D2C 인텔리전스 주간 리포트를 자동으로 생성하기 위한 실행 템플릿입니다.

## 1) 목표
- 핵심 법인(16개국) x 5개 카테고리 x 4개 Pillar 신호를 주 단위로 수집
- 모든 데이터 포인트에 검증 가능한 URL을 부착
- 경영진 보고서(Markdown) + 공유용 HTML 동시 생성
- Codex 1차 작성 + Claude Co-work 2차 검증(옵션)

## 2) 디렉토리 구조
- `config/`: 환경설정
- `prompts/`: 수집/분석/검증 프롬프트
- `data/raw/`: 원천 데이터
- `data/normalized/`: 정규화 데이터
- `data/weekly/`: 주간 집계 산출물
- `reports/md/`: 최종 Markdown 리포트
- `reports/html/`: 최종 HTML 리포트
- `scripts/`: 파이프라인 실행 스크립트
- `qa/`: 검증 결과(링크 무결성, 누락 체크)

## 3) 실행 방법
1. 환경설정 준비
```bash
cp config/pipeline.env.example config/pipeline.env
```

2. (선택) OpenClaw/Claude 실행 커맨드 연결
- `config/pipeline.env`의 `OPENCLAW_RUNNER`, `CLAUDE_RUNNER` 설정
- 기본은 example runner로 안전하게 동작
- 실제 CLI 연동은 아래처럼 전환
```bash
OPENCLAW_RUNNER="/Users/soonho/Documents/New project/d2c-intel/agents/openclaw_runner_cli.sh"
CLAUDE_RUNNER="/Users/soonho/Documents/New project/d2c-intel/agents/claude_runner_cli.sh"
OPENCLAW_AGENT_ID="main"
CLAUDE_MODEL="sonnet"
```

3. 주간 파이프라인 실행
```bash
bash scripts/run_weekly.sh
```
- 위 명령 1회로 수집/초안/검수 + HTML/PDF/Hub 빌드 + (옵션) Obsidian export까지 수행됩니다.

4. (옵션) Obsidian 주차 폴더/페이지 자동 생성
- `config/pipeline.env`에 아래 설정 추가
```bash
ENABLE_OBSIDIAN_EXPORT=1
OBSIDIAN_WEEKLY_ROOT="/Users/soonho/Documents/Obsidian MacMini/Global D2C Weekly Intelligence"
```
- 실행 시 `YYYY-MM-DD Weekly Intelligence` 폴더와 요약 페이지가 자동 생성됩니다.

5. 결과물 확인
- Markdown: `reports/md/LG_Global_D2C_Weekly_Intelligence_[YYYY-MM-DD].md`
- HTML: `reports/html/[YYYY-MM-DD]/index.html`
- Hub: `reports/html/latest/hub.html`
- PDF: `reports/pdf/LG_Global_D2C_Weekly_Intelligence_[YYYY-MM-DD]_R2_16country.pdf`
- QA 로그: `qa/qa_summary_[YYYY-MM-DD].md`
- Obsidian: `[Vault]/Global D2C Weekly Intelligence/[YYYY-MM-DD Weekly Intelligence]/README.md`

## 3-1) 회사 공유 폴더 자동 업로드 + Teams 알림
`run_weekly.sh` 실행 후 아래 단계가 자동으로 이어지게 구성할 수 있습니다.

1. 공유 폴더 업로드
- `ENABLE_SHARED_PUBLISH=1`
- `SHARED_PUBLISH_ROOT="/회사공유드라이브/Global D2C Weekly Intelligence"`
- 산출물 복사 구조:
  - `weekly/[YYYY-MM-DD]/html|pdf|md`
  - `latest/html|pdf|manifest`

2. Teams 자동 알림
- `ENABLE_TEAMS_NOTIFY=1`
- `TEAMS_WEBHOOK_URL="https://...office.com/webhook/..."`
- `SHARED_BASE_URL="https://<사내포털>/global-d2c-weekly"` 설정 시 메시지에 사내 링크 포함

3. 테스트 모드
- `TEAMS_DRY_RUN=1`로 두면 Teams 전송 없이 payload만 출력

`config/pipeline.env` 예시:
```bash
ENABLE_SHARED_PUBLISH=1
SHARED_PUBLISH_ROOT="/Volumes/CompanyShare/Global D2C Weekly Intelligence"
SHARED_BASE_URL="https://intranet.company.com/d2c"
ENABLE_TEAMS_NOTIFY=1
TEAMS_WEBHOOK_URL="https://..."
TEAMS_DRY_RUN=0
```

## 4) Co-work 운영 권장안
- OpenClaw: 대량 수집(다국어/다국가)
- Codex: 구조화/정규화/초안 작성
- Claude Co-work: 리스크 탐지, 누락/과장/근거 부족 검토, 문장 품질 강화
- 상세 운영법: `agents/CLAUDE_COWORK_PLAYBOOK.md`

## 5) 운영 체크리스트
- 모든 사실/수치/인용에 `[🔗 Source](URL)` 포함
- URL 미검증 데이터는 `❓[출처 미확인 — 검색어: "..."]` 처리
- 경영진 요약의 P1/P2/P3 액션에 Owner/Deadline 명시
- 섹션 누락 시 배포 금지(Draft 표기)
- HTML/PDF 디자인 자동 규칙 확인:
  - `##` 섹션 제목은 배너 스타일
  - `### 핵심 인사이트` / `### 실행 필요`는 각각 강조 배너 스타일
  - 기준 렌더러: `scripts/render_professional_report.mjs`

## 6) 자동 스케줄 예시 (KST 월요일 04:00)
macOS `launchd` 등록:
```bash
bash scripts/install_launchd_weekly.sh
```

등록 해제:
```bash
bash scripts/uninstall_launchd_weekly.sh
```

기본 스케줄은 월요일 04:00 KST이며, 환경변수로 변경 가능합니다.
- `LAUNCHD_WEEKDAY` (기본: `1`, 월요일)
- `LAUNCHD_HOUR` (기본: `4`)
- `LAUNCHD_MINUTE` (기본: `0`)

## 7) 개인 PC 링크 공유 (ngrok)
로컬 보고서를 링크로 외부 공유할 때:

```bash
bash scripts/install_public_share_services.sh
bash scripts/get_public_share_link.sh
```

- Local Hub: `http://localhost:8090/html/latest/hub.html`
- Public Hub: `https://...ngrok-free.dev/html/latest/hub.html`

중지/삭제:
```bash
bash scripts/uninstall_public_share_services.sh
```

## 8) 최신 반영 고정 규칙 (2026-02 업데이트)
향후 주차 자동 생성에도 아래 규칙을 고정 적용한다.

- 보고서 본문/제목/타이틀은 한글 우선으로 작성한다.
- 국가 표기는 `국기 + 국가명 (+국가코드)` 형식으로 통일한다.
  - 예: `🇺🇸 미국 (US)`, `🇩🇪 독일 (DE)`
- 용어는 `MS`/`HS`만 사용한다.
  - `MS = Media Entertainment Solution`
  - `HS = Home appliance solution`
  - `HE`, `H&A`는 금지한다.
- `목차(Table of Contents)` 섹션은 생성하지 않는다.
- `핵심 인사이트`/`실행 필요`는 본문 주요 섹션에만 포함하고 Appendix에는 작성하지 않는다.
- HTML 왼쪽 숏컷 메뉴는 한글 라벨과 계층형 들여쓰기를 유지한다.
- 허브는 한국어(`hub.html`) + 영어(`hub_en.html`) 2개를 유지한다.
- 허브 PDF 링크는 반드시 상대경로(`../pdf/...`)를 사용한다.
  - `file:///...` 절대경로는 금지한다.
- 영어 리포트(`index_en.html`)는 전면 영어로 유지하고 한글 잔존을 허용하지 않는다.

## 9) 배포 전 최소 점검 명령
```bash
# 1) EN 페이지 한글 잔존 확인 (출력 없어야 정상)
rg -n "[가-힣]" reports/html/*/index_en.html

# 2) 허브 PDF 링크 확인 (file:// 없어야 정상)
rg -n "file://" reports/html/latest/hub.html reports/html/latest/hub_en.html

# 3) 최신 허브 링크 확인
rg -n "index_en.html|\\.pdf" reports/html/latest/hub_en.html
```
