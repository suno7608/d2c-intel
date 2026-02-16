# D2C Weekly Intelligence Report — Format Specification (v2.0)

이 문서는 주간 리포트의 **고정 포맷**을 정의한다. 모든 리포트는 이 명세를 준수해야 한다.
참조 기준: 2026-02-14 R2 핵심 법인 리포트

---

## 1. 문서 헤더 (고정)

```
# LG전자 글로벌 D2C 주간 시장 인텔리전스 리포트 (R2, 핵심 법인 풀 커버리지)

소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향

보고 기간: YYYY-MM-DD(일) — YYYY-MM-DD(토)
Prepared by: D2C Global Intelligence (OpenClaw Automated)
Distribution: D2C Leadership / Confidential
Date Generated: YYYY-MM-DD
Version: Weekly Vol.YYYY-MM-DD-R2
```

보고 기간은 **전주 일요일 ~ 토요일** (7일 고정).

---

## 2. 섹션 구조 (고정, 순서 변경 금지)

### Section 1: 경영진 요약
- 핵심 인사이트 (3개 bullet, 전략적 해석)
- 실행 필요 (3개 numbered, 구체적 실행 지시)
- 1.1 핵심 발견 (테이블: #, Category, Finding, Country-Product, Severity, Detail)
  - ⚠️ **TV 외 제품(냉장고/세탁기/모니터/gram)도 반드시 포함** — TV만 나열 금지
- 1.2 이번 주 주요 지표 (테이블: Metric, This Week, vs Last Week, Trend)
  - 제품별 데이터 건수 포함
- 1.3 권장 실행 과제 (테이블: Priority, Action, Target Country, Target Product, Owner, Deadline)
  - TV 외 제품 관련 액션도 포함

### Section 2: 핵심 경보
- 핵심 인사이트 + 실행 필요
- 2.1 핵심 법인 알림 맵 (테이블: Country, Alert, Severity, 근거 — **16개국 모두 포함**)
- 2.2 소비자 부정 알림 (테이블: #, Country, Product, Issue, Severity, Source)
  - 냉장고/세탁기 A/S 불만 데이터 반드시 반영
- 2.3 경쟁사 공격 행보 (테이블: #, Country, Competitor, Action, LG Impact, Source)
- 2.4 중국 브랜드 모멘텀 알림 (테이블: Country, Brand, Signal, Threat, Source)
  - ⚠️ **TV뿐 아니라 가전(냉장고/세탁기) 중국 브랜드 위협도 포함**

### Section 3: 핵심 법인 풀 커버리지 대시보드
- 핵심 인사이트 + 실행 필요
- 3.1 소비자 반응 모니터링 (핵심 인사이트 + 실행 필요 + 핵심 법인 테이블)
- 3.2 유통 채널 프로모션 모니터링 (핵심 인사이트 + 실행 필요 + 핵심 법인 테이블)
- 3.3 경쟁 가격 및 포지셔닝 (핵심 인사이트 + 실행 필요 + 핵심 비교 테이블)
  - ⚠️ **제품별 가격 비교**: TV, 냉장고, 세탁기, 모니터 각각 핵심 비교 포함
- 3.4 중국 브랜드 위협 추적 (핵심 인사이트 + 실행 필요 + 핵심 법인 테이블)
  - ⚠️ **TV + 가전 모두 커버** — Haier/Midea 냉장고·세탁기 위협 포함

### Section 4: 중국 브랜드 위협 보고
- 핵심 인사이트 + 실행 필요
- 4.1 브랜드별 분석 (테이블)
  - TCL, Hisense: TV 중심
  - Haier, Midea: **가전(냉장고/세탁기) 중심** — 별도 분석 필수
- 4.2 중국 브랜드 가격 전쟁 맵 (핵심국가 가격 비교 테이블)
  - TV + 냉장고 + 세탁기 가격 비교 모두 포함
- 4.3 전략 요약 (텍스트)

### Section 5: 전주 대비 추이
- 핵심 인사이트 + 실행 필요
- W-o-W 트렌드 테이블 (Metric, W-4~This Week, Trend)

### Appendix A: 데이터 소스 및 커버리지
- 16개국 소스 테이블 (핵심 인사이트/실행 필요 없음)
- **국가별 제품 커버리지 표시** (어떤 국가에 어떤 제품 데이터가 있는지)

### Appendix B: 방법론 및 한계
- 수집 범위, 링크 규칙, 제한사항 (핵심 인사이트/실행 필요 없음)
- **국가별 데이터 밀도 편차 명시** (Tier 1/2/3 분류)

### Appendix C: 용어집
- 용어 테이블 (핵심 인사이트/실행 필요 없음)

---

## 3. 핵심 인사이트 + 실행 필요 블록 규칙

모든 주요 섹션(1~5)과 서브섹션(3.1~3.4)에 **반드시** 포함:

```markdown
### 핵심 인사이트
- [전략적 해석 1]
- [전략적 해석 2]
- [전략적 해석 3]

### 실행 필요
1. [구체적 실행 지시 — 국가/제품/기한 포함]
2. [구체적 실행 지시]
3. [구체적 실행 지시]
```

예외: Appendix A/B/C에는 작성하지 않는다.

---

## 4. 표기 규칙

### 국가 표기
- 반드시 `국기 + 국가명 (+국가코드)` 형식으로 작성한다.
- 권장 예시:
  - 🇺🇸 미국 (US), 🇨🇦 캐나다 (CA), 🇬🇧 영국 (UK), 🇩🇪 독일 (DE)
  - 🇫🇷 프랑스 (FR), 🇪🇸 스페인 (ES), 🇮🇹 이탈리아 (IT), 🇧🇷 브라질 (BR)
  - 🇲🇽 멕시코 (MX), 🇨🇱 칠레 (CL), 🇹🇭 태국 (TH), 🇦🇺 호주 (AU)
  - 🇹🇼 대만 (TW), 🇸🇬 싱가포르 (SG), 🇪🇬 이집트 (EG), 🇸🇦 사우디아라비아 (SA)

### Severity 표기
- 🔴 Critical / 🟡 Warning / 🟢 Normal

### Priority 표기
- 🔴 P1 / 🟡 P2 / 🟢 P3

### Source 링크
- 실제 URL: `[🔗 Source](https://...)`
- URL 미확보: `❓[출처 미확인 — 검색어: "..."](https://www.google.com/search?q=...)`

### 용어
- MS = Media Entertainment Solution (TV 사업)
- HS = Home appliance solution (생활가전)
- HE, H&A는 사용하지 않는다

### 언어
- 본문: 한국어
- 영어 유지: 브랜드명, 모델명, 리테일러명, URL, 기술 용어
- 영어판(`index_en.html`)은 본문/인용/배너 텍스트까지 영어로 작성하며 한글 잔존을 허용하지 않는다.

---

## 5. 콘텐츠 균형 규칙

### 제품 균형
- 리포트 내 TV 관련 콘텐츠가 **전체의 50%를 초과하면 안 됨**
- 냉장고/세탁기/모니터/gram 인사이트를 Key Findings, Alerts, Dashboard 전반에 균형 배치
- **1.1 Key Findings에 TV 외 제품 최소 3건** 포함

### 국가별 깊이 균형
- Tier 1(US/UK/DE/AU/BR): 풍부한 분석 (다제품, 다Pillar)
- Tier 2(FR/IT/ES/TH/SA/CA): 중간 분석
- Tier 3(TW/SG/EG/CL/MX): **TV 외 제품 인사이트도 반드시 포함** — TV만 있는 국가 없어야 함

### 중국 브랜드 커버리지
- Section 4에서 **TV 중국 브랜드(TCL/Hisense)와 가전 중국 브랜드(Haier/Midea)를 분리 분석**
- 4.2 Price War Map에 TV + 냉장고 + 세탁기 가격 비교 모두 포함

---

## 6. 품질 기준

- 파일 크기: **최소 55KB** (65KB+ 권장)
- 16개국 **모두** 각 주요 테이블에 포함 (빠진 국가 없어야 함)
- 모든 테이블 행에 Source 링크 포함
- 목차(Table of Contents) 섹션은 생성하지 않는다
- 섹션 번호 일관성 유지 (1, 2, 3, 4, 5, Appendix A/B/C)
- **제품 균형 체크**: Key Findings 10건 중 TV 외 제품 3건+
- **데이터 건수 기준**: 전체 200건+, 냉장고 40건+, 세탁기 35건+, 모니터 15건+, gram 10건+
- 영어 HTML(`reports/html/[YYYY-MM-DD]/index_en.html`)에서 한글 문자열 검색 결과가 0건이어야 한다.

---

## 7. HTML 시각 디자인 규칙 (자동 렌더 반영)

주간 HTML/PDF는 `scripts/render_professional_report.mjs` 기준으로 아래 스타일이 자동 적용되어야 한다.

- `##` 섹션 제목(`.section-title`)은 **허브 스타일 그라데이션 띠 배너**로 표시한다.
  - 대상 예: `1. 경영진 요약`, `2. 핵심 경보` 등
- `###` 소제목(`.sub-title`)은 카드형 배너로 표시한다.
- `### 핵심 인사이트`는 파란 강조 배너(`.key-insight-banner`)로 표시한다.
- `### 실행 필요`는 노란 강조 배너(`.action-required-banner`)로 표시한다.
- TOC에는 `핵심 인사이트`, `실행 필요`를 계속 제외한다.
- 인쇄/ PDF 출력 시에는 가독성을 위해 배경색을 제거한 단색 스타일로 자동 전환한다.
- 왼쪽 숏컷(TOC) 라벨은 한글로 표시하고, 3.1/3.2/3.3/3.4는 계층형 들여쓰기로 가독성을 확보한다.
- 허브(`reports/html/latest/hub.html`)는 `주간 아카이브 탐색기`, `전주 대비 비교` 배너를 유지한다.
- 허브 영어판(`reports/html/latest/hub_en.html`)은 `WEEKLY ARCHIVE EXPLORER`, `WEEK-OVER-WEEK COMPARE` 배너를 유지한다.
- 허브 PDF 링크는 `../pdf/<파일명>.pdf` 상대경로만 허용하며 `file:///` 링크는 금지한다.
