# D2C Weekly Intelligence Pipeline

> **Automated weekly intelligence report generator** — collects global D2C signals, normalizes data, and produces executive-ready reports (Markdown / HTML / PDF).

글로벌 D2C(Direct-to-Consumer) 인텔리전스 주간 리포트를 자동 생성하는 파이프라인입니다. 다국가 × 다카테고리 신호를 수집하고, AI 기반 분석·검증을 거쳐 경영진 보고서를 생성합니다.

[![Shell](https://img.shields.io/badge/Shell-Bash-green)](scripts/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-brightgreen)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org/)
[![License](https://img.shields.io/badge/License-Private-lightgrey)]()

---

## 📑 Table of Contents

- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Goals](#1-goals--목표)
- [Directory Structure](#2-directory-structure--디렉토리-구조)
- [Running the Pipeline](#3-running-the-pipeline--실행-방법)
- [Shared Folder Upload & Teams Notification](#3-1-shared-folder-upload--teams-notification--회사-공유-폴더-자동-업로드--teams-알림)
- [Co-work Strategy](#4-co-work-strategy--co-work-운영-권장안)
- [Operations Checklist](#5-operations-checklist--운영-체크리스트)
- [Scheduled Automation](#6-scheduled-automation--자동-스케줄)
- [Public Link Sharing (ngrok)](#7-public-link-sharing-ngrok--개인-pc-링크-공유)
- [Report Style Rules](#8-report-style-rules--최신-반영-고정-규칙)
- [Pre-deploy Checks](#9-pre-deploy-checks--배포-전-최소-점검-명령)
- [Translation / Quality Pipeline](#10-translation--quality-pipeline--번역품질-파이프라인-변경점)

---

## 🏗 Architecture

전체 파이프라인 흐름도 / End-to-end pipeline flow:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    D2C Weekly Intelligence Pipeline                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ① Collect           ② Normalize         ③ Draft                   │
│  ┌──────────┐       ┌──────────┐       ┌──────────────┐            │
│  │ OpenClaw │──────▶│  Scripts  │──────▶│ Codex / AI   │            │
│  │ (multi-  │       │ (merge & │       │ (structured  │            │
│  │  country │       │  clean)  │       │  draft)      │            │
│  │  signals)│       └──────────┘       └──────┬───────┘            │
│  └──────────┘                                 │                     │
│       ▲                                       ▼                     │
│       │              ④ Co-work          ┌──────────────┐            │
│  prompts/            (optional)         │ Claude       │            │
│  config/             ◀─────────────────▶│ (review &    │            │
│                                         │  enhance)    │            │
│                                         └──────┬───────┘            │
│                                                │                     │
│  ┌──────────────┐                               │                     │
│  │ Brave Search │──────────────┐               │                     │
│  │ + Scrapling  │ fresh        │               │                     │
│  │ fallback     │ fallback     │               │                     │
│  └──────────────┘──────────────┘               │                     │
│                                                │                     │
│                     ⑤ Render & QA              ▼                     │
│                   ┌───────────────────────────────────┐             │
│                   │  render HTML/PDF │ quality gate   │             │
│                   │  translate (EN)  │ link check     │             │
│                   └────────┬─────────┴───────┬────────┘             │
│                            ▼                 ▼                       │
│                   ┌──────────────┐  ┌──────────────┐               │
│                   │ reports/     │  │ qa/           │               │
│                   │  md/html/pdf │  │  summary      │               │
│                   └──────┬───────┘  └──────────────┘               │
│                          ▼                                          │
│              ⑥ Publish (optional)                                   │
│              ┌─────────────────────────────┐                        │
│              │ Obsidian │ Shared Drive │    │                        │
│              │ ngrok    │ Teams notify │    │                        │
│              └─────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| **Bash** | 4+ | Pipeline scripts |
| **Node.js** | 18+ | HTML/PDF rendering (`render_professional_report.mjs`) |
| **Python** | 3.10+ | Translation fallback (Google Translate) |
| **OpenClaw CLI** | latest | AI agent runner for primary data collection |
| **Brave Search API** | latest | Fresh fallback discovery when OpenClaw fails |
| **Claude CLI** | latest | Co-work review & translation |
| **gh CLI** | latest | GitHub integration (optional) |
| **ripgrep (`rg`)** | any | Quality gate checks |
| **ngrok** | any | Public link sharing (optional) |
| **Scrapling parser deps** | latest | Result-page enrichment for stronger evidence |

```bash
# macOS (Homebrew)
brew install node python gh ripgrep ngrok
# OpenClaw / Claude — see respective docs
```

---

## 🚀 Quick Start

```bash
# 1. Clone / 클론
git clone https://github.com/<your-org>/d2c-intel.git
cd d2c-intel

# 2. Configure / 환경설정
cp config/pipeline.env.example config/pipeline.env
# Edit config/pipeline.env — set runner paths, agent IDs, etc.

# 3. (Optional) Set up Python venv for translation fallback
python3 -m venv .venv-trans
source .venv-trans/bin/activate
pip install googletrans==4.0.0-rc1

# 4. Run the weekly pipeline / 주간 파이프라인 실행
bash scripts/run_weekly.sh

# 5. Check outputs / 결과 확인
open reports/html/latest/hub.html      # Hub page
open reports/md/                        # Markdown reports
cat qa/qa_summary_*.md                  # QA results
```

> 💡 **Tip:** `config/pipeline.env.example`에 모든 설정 항목과 설명이 있습니다. 복사 후 환경에 맞게 수정하세요.

---

## 1) Goals / 목표
- 핵심 법인(다국가) × 카테고리 × Pillar 신호를 주 단위로 수집
- 모든 데이터 포인트에 검증 가능한 URL 부착
- 경영진 보고서(Markdown) + 공유용 HTML 동시 생성
- Codex 1차 작성 + Claude Co-work 2차 검증(옵션)

## 2) Directory Structure / 디렉토리 구조
- `config/`: 환경설정 (pipeline.env 등)
- `prompts/`: 수집/분석/검증 프롬프트
- `data/raw/`: 원천 데이터
- `data/normalized/`: 정규화 데이터
- `data/weekly/`: 주간 집계 산출물
- `reports/md/`: 최종 Markdown 리포트
- `reports/html/`: 최종 HTML 리포트
- `reports/pdf/`: 최종 PDF 리포트
- `scripts/`: 파이프라인 실행 스크립트
- `qa/`: 검증 결과(링크 무결성, 누락 체크)
- `agents/`: AI runner 스크립트

## 3) Running the Pipeline / 실행 방법

### 3-1. Environment Setup / 환경설정 준비
```bash
cp config/pipeline.env.example config/pipeline.env
```

### 3-2. (Optional) Configure AI Runners / OpenClaw·Claude 연결
`config/pipeline.env`에서 runner 경로와 에이전트 설정:
```bash
# Example — adjust paths to your environment
OPENCLAW_RUNNER="./agents/openclaw_runner_cli.sh"
CLAUDE_RUNNER="./agents/claude_runner_cli.sh"
OPENCLAW_AGENT_ID="main"
OPENCLAW_ALT_AGENT_IDS="alt_agent,main"
CLAUDE_MODEL="sonnet"
```

영어 번역 자동화를 커스텀으로 붙일 경우 `CLAUDE_TRANSLATE_RUNNER` 설정 (인자: `prompt input_md output_md`)

### 3-3. Run Weekly Pipeline / 주간 파이프라인 실행
```bash
bash scripts/run_weekly.sh
```
- 1회 실행으로 수집/초안/검수 + 한/영 HTML/PDF/Hub 빌드 + 품질 게이트 + (옵션) Obsidian export까지 수행
- **실패 조건** (자동 중단):
  - OpenClaw runner 미설정 (placeholder fallback 기본 금지)
  - Claude co-work runner 미설정 (fallback copy 기본 금지)
  - 영어 번역 실패 (Claude + Google fallback 모두 실패) 또는 품질 실패
  - 품질 게이트 미통과 (데이터 최소치/metadata/hub 링크 등)
- **안정화 옵션:**
  - `ENABLE_PREFLIGHT_CHECK=1`: 실행 전 환경 점검
  - `ENABLE_BRAVE_SEARCH_FALLBACK=1`: OpenClaw 실패 시 Brave Search + Scrapling 기반 fresh fallback 실행
  - `ENABLE_OPENCLAW_LAST_SUCCESS_FALLBACK=1`: 수집 실패 시 최근 정상 raw 재사용
  - `OPENCLAW_MAX_RETRIES=3`: OpenClaw 재시도 횟수
  - `OPENCLAW_BACKOFF_BASE_SECONDS=10`: 지수 백오프 기본값
  - `OPENCLAW_RATE_LIMIT_EXTRA_SECONDS=25`: 429 발생 시 추가 대기
  - `OPENCLAW_SESSION_LOCK_EXTRA_SECONDS=15`: session lock 발생 시 추가 대기
  - `OPENCLAW_ENABLE_STALE_LOCK_CLEANUP=1`: dead PID stale lock 안전 정리
  - `OPENCLAW_ADAPTIVE_POLICY_MAX_LEVEL=3`: 반복 실패 패턴 강화 레벨 상한
  - `ENABLE_SCRAPLING_ENRICHMENT=1`: 검색 결과 URL 본문을 추가 파싱하여 title/summary/price evidence 강화
  - `FAIL_ON_STALE_COLLECTION=1`: fallback 재사용 시 배포 차단 (엄격 모드)
- **진단 로그:**
  - `logs/openclaw_[DATE].diag.jsonl` — attempt/원인/백오프/요약
  - `logs/openclaw_[DATE].collection.jsonl` — primary/fallback 단계 기록
  - `logs/openclaw_adaptive_policy.env` — 다음 실행 정책 강화 상태

### 3-4. (Optional) Obsidian Export
`config/pipeline.env`에 아래 설정 추가:
```bash
ENABLE_OBSIDIAN_EXPORT=1
OBSIDIAN_WEEKLY_ROOT="/path/to/your/obsidian-vault/Weekly Intelligence"
```

### 3-5. Output Files / 결과물 확인
| Type | Path |
|------|------|
| Markdown | `reports/md/..._Weekly_Intelligence_[YYYY-MM-DD].md` |
| HTML | `reports/html/[YYYY-MM-DD]/index.html` |
| Hub | `reports/html/latest/hub.html` |
| PDF | `reports/pdf/..._Weekly_Intelligence_[YYYY-MM-DD].pdf` |
| QA | `qa/qa_summary_[YYYY-MM-DD].md` |
| Obsidian | `[Vault]/Weekly Intelligence/[YYYY-MM-DD]/README.md` |

## 3-1) Shared Folder Upload & Teams Notification / 회사 공유 폴더 자동 업로드 + Teams 알림

`run_weekly.sh` 실행 후 아래 단계가 자동으로 이어지게 구성할 수 있습니다.

### Upload to Shared Drive / 공유 폴더 업로드
```bash
ENABLE_SHARED_PUBLISH=1
SHARED_PUBLISH_ROOT="/path/to/shared-drive/Weekly Intelligence"
```
산출물 복사 구조: `weekly/[YYYY-MM-DD]/html|pdf|md`, `latest/html|pdf|manifest`

### Teams Auto-notification / Teams 자동 알림
```bash
ENABLE_TEAMS_NOTIFY=1
TEAMS_WEBHOOK_URL="https://...office.com/webhook/..."
SHARED_BASE_URL="https://<your-portal>/weekly"  # 메시지에 링크 포함
TEAMS_DRY_RUN=1  # 테스트 시 1로 설정
```

## 4) Co-work Strategy / Co-work 운영 권장안
- **OpenClaw**: 대량 수집 (다국어/다국가)
- **Codex**: 구조화/정규화/초안 작성
- **Claude Co-work**: 리스크 탐지, 누락/과장/근거 부족 검토, 문장 품질 강화
- 상세 운영법: `agents/CLAUDE_COWORK_PLAYBOOK.md`

## 5) Operations Checklist / 운영 체크리스트
- 모든 사실/수치/인용에 `[🔗 Source](URL)` 포함
- URL 미검증 데이터는 `❓[출처 미확인 — 검색어: "..."]` 처리
- 경영진 요약의 P1/P2/P3 액션에 Owner/Deadline 명시
- 섹션 누락 시 배포 금지 (Draft 표기)
- HTML/PDF 디자인 자동 규칙:
  - `##` 섹션 제목은 배너 스타일
  - `### 핵심 인사이트` / `### 실행 필요`는 강조 배너 스타일
  - 기준 렌더러: `scripts/render_professional_report.mjs`
- 자동 품질 게이트 (`scripts/quality_gate_weekly.sh`) 통과 확인:
  - 국가별/제품별 최소 건수
  - English MD/HTML 한글 잔존 여부
  - Hub `file://` 링크 여부
  - metadata null 및 Critical 국가 형식 이상 여부
- 영어 번역 경로:
  - 1차: Claude 번역 (`translate_report_to_english.sh`)
  - 2차 fallback: Google Translate API (`ENABLE_GOOGLE_TRANSLATE_FALLBACK=1`)
  - 3차 fallback: Offline English stub (`ENABLE_OFFLINE_EN_STUB_FALLBACK=1`)

## 6) Scheduled Automation / 자동 스케줄

예시: macOS `launchd` — 매주 월요일 04:00 KST:
```bash
bash scripts/install_launchd_weekly.sh        # 등록
bash scripts/install_launchd_preflight.sh     # 사전점검 등록 (03:30)
bash scripts/uninstall_launchd_weekly.sh      # 해제
bash scripts/uninstall_launchd_preflight.sh   # 해제
```
환경변수로 스케줄 변경 가능: `LAUNCHD_WEEKDAY`, `LAUNCHD_HOUR`, `LAUNCHD_MINUTE`

## 7) Public Link Sharing (ngrok) / 개인 PC 링크 공유

로컬 보고서를 링크로 외부 공유:
```bash
bash scripts/install_public_share_services.sh
bash scripts/get_public_share_link.sh
```
- Local Hub: `http://localhost:8090/html/latest/hub.html`
- Public Hub: `https://<ngrok-subdomain>.ngrok-free.dev/html/latest/hub.html`

중지/삭제: `bash scripts/uninstall_public_share_services.sh`

## 8) Report Style Rules / 최신 반영 고정 규칙

> 2026-02 업데이트 — 향후 주차 자동 생성에도 아래 규칙을 고정 적용합니다.

- 보고서 본문/제목/타이틀은 한글 우선 작성
- 국가 표기: `국기 + 국가명 (+국가코드)` — 예: `🇺🇸 미국 (US)`, `🇩🇪 독일 (DE)`
- HTML 왼쪽 숏컷 메뉴는 한글 라벨과 계층형 들여쓰기 유지
- 허브는 한국어(`hub.html`) + 영어(`hub_en.html`) 2개 유지
- 허브 PDF 링크는 반드시 상대경로(`../pdf/...`) — `file:///` 절대경로 금지
- 영어 리포트(`index_en.html`)는 전면 영어 유지, 한글 잔존 불허

## 9) Pre-deploy Checks / 배포 전 최소 점검 명령
```bash
# EN 페이지 한글 잔존 확인 (출력 없어야 정상)
rg -n "[가-힣]" reports/html/*/index_en.html

# 허브 PDF 링크 확인 (file:// 없어야 정상)
rg -n "file://" reports/html/latest/hub.html reports/html/latest/hub_en.html

# 최신 허브 링크 확인
rg -n "index_en.html|\\.pdf" reports/html/latest/hub_en.html
```

## 10) Translation / Quality Pipeline / 번역·품질 파이프라인 변경점
- EN 보고서: `KO Markdown → EN Markdown (Claude) → EN HTML 렌더` 경로로 생성
- 기존 HTML 치환 기반 번역 (`render_report_english_variant.mjs`)은 폐기 (호환용 에러 스텁만 유지)
- 자동 품질 게이트: `scripts/quality_gate_weekly.sh` — 실패 시 후속 배포 중단

---

## 📄 License

Private / Internal use.
