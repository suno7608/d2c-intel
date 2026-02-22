# D2C Monthly Deep Dive Intelligence Report — Format Specification (v1.0)

이 문서는 월간 심화 분석 리포트의 **고정 포맷**을 정의한다.
모든 Monthly 리포트는 이 명세를 준수해야 한다.
참조 기준: Weekly Format Spec v2.0 + Monthly 확장

---

## 1. 문서 헤더 (고정)

```
# LG전자 글로벌 D2C 월간 시장 심화 분석 리포트 (Monthly Deep Dive)

소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향 — 월간 추세 분석

보고 기간: YYYY-MM-01 — YYYY-MM-말일
데이터 기반: 주간 리포트 N회분 (Vol.YYYY-MM-DD-R2 ~ Vol.YYYY-MM-DD-R2)
Prepared by: D2C Global Intelligence (OpenClaw Automated)
Distribution: D2C Leadership / Confidential
Date Generated: YYYY-MM-DD
Version: Monthly Vol.YYYY-MM
```

보고 기간은 **해당 월 1일 ~ 말일** (전월 분석).

---

## 2. 섹션 구조 (고정, 순서 변경 금지)

### Section 1: 월간 경영진 요약
- 핵심 인사이트 (5개 bullet, 월간 전략적 트렌드)
- 실행 필요 (5개 numbered, 중장기 실행 과제)
- 1.1 월간 핵심 발견 (테이블: #, Category, Finding, Country-Product, Severity, Trend vs Last Month)
  - ⚠️ **TV 외 제품(냉장고/세탁기/모니터/gram)도 반드시 포함** — TV만 나열 금지
  - 최소 12건, TV 외 제품 최소 4건
- 1.2 월간 주요 지표 (테이블: Metric, This Month, vs Last Month, 4-Week Trend, MoM Change%)
  - 제품별 데이터 건수 포함
  - `<!-- CHART:monthly_kpi_summary -->` 마커 삽입
- 1.3 전략 과제 로드맵 (테이블: Priority, Action, Target Country, Target Product, Owner, Timeline)

### Section 2: 월간 핵심 경보 종합
- 핵심 인사이트 + 실행 필요
- 2.1 핵심 법인 월간 경보 추이 (테이블: Country, W1 Alert, W2 Alert, W3 Alert, W4 Alert, Monthly Trend)
  - **16개국 모두 포함**, 주차별 Alert Severity 변화를 보여줌
  - `<!-- CHART:monthly_country_heatmap -->` 마커 삽입
- 2.2 소비자 부정 반응 월간 추이 (테이블: Country, Product, W1~W4 Issues, Trend)
  - 냉장고/세탁기 A/S 불만 추세 반드시 포함
- 2.3 경쟁사 공격 행보 월간 타임라인 (테이블: Week, Country, Competitor, Action, LG Impact)
- 2.4 중국 브랜드 모멘텀 월간 분석 (테이블: Brand, Country, W1~W4 Signal Count, Trend)
  - ⚠️ **TV + 가전 모두 커버**

### Section 3: 16개국 월간 대시보드
- 핵심 인사이트 + 실행 필요
- 3.1 소비자 반응 월간 추이 (핵심 인사이트 + 실행 필요 + 16개국 테이블)
  - `<!-- CHART:monthly_sentiment_trend -->` 마커 삽입
- 3.2 유통 채널 프로모션 월간 추이 (핵심 인사이트 + 실행 필요 + 16개국 테이블)
  - `<!-- CHART:monthly_promo_timeline -->` 마커 삽입
- 3.3 경쟁 가격 월간 포지셔닝 분석 (핵심 인사이트 + 실행 필요 + 핵심 비교 테이블)
  - ⚠️ **제품별 가격 트렌드**: TV, 냉장고, 세탁기, 모니터 각각 월간 비교
- 3.4 중국 브랜드 위협 월간 추적 (핵심 인사이트 + 실행 필요 + 16개국 테이블)

### Section 4: 제품별 Deep Dive 분석
- 핵심 인사이트 + 실행 필요
- 4.1 TV (MS) Deep Dive
  - 월간 프로모션 사이클, 가격 변동, 경쟁사 대응 분석
  - TCL/Hisense 공세 월간 추이
  - `<!-- CHART:monthly_tv_deep_dive -->` 마커 삽입
- 4.2 냉장고/세탁기 (HS) Deep Dive
  - 월간 소비자 반응 패턴, Haier/Midea 위협 추이
  - `<!-- CHART:monthly_appliance_deep_dive -->` 마커 삽입
- 4.3 모니터/LG gram Deep Dive
  - 월간 가격 포지셔닝, 프로모션 효과 분석

### Section 5: 중국 브랜드 월간 위협 보고
- 핵심 인사이트 + 실행 필요
- 5.1 브랜드별 월간 추이 (TCL, Hisense, Haier, Midea 각각)
  - `<!-- CHART:monthly_china_brand_bar -->` 마커 삽입
- 5.2 중국 브랜드 가격 전쟁 월간 맵 (국가별 × 제품별 가격 비교)
- 5.3 전략 요약 및 대응 방안

### Section 6: Month-over-Month 트렌드
- 핵심 인사이트 + 실행 필요
- M-o-M 트렌드 테이블 (Metric, M-3, M-2, Last Month, This Month, Trend)
  - `<!-- CHART:monthly_mom_trend -->` 마커 삽입

### Section 7: 차트 갤러리
- 본 섹션의 모든 차트는 Chart.js 인터랙티브 차트로 렌더링됨
- 7.1 국가별 시그널 히트맵
- 7.2 제품별 4주 추이 라인차트
- 7.3 중국 브랜드 월간 비교 바차트
- 7.4 소비자 반응 분포 파이차트
- 각 차트 아래에 JSON 데이터 블록 포함 (렌더러가 파싱)

### Appendix A: 데이터 소스 및 커버리지
- 월간 16개국 소스 테이블 (핵심 인사이트/실행 필요 없음)
- 주차별 수집 건수 테이블 (W1~W4)
- **국가별 제품 커버리지 히트맵**

### Appendix B: 방법론 및 한계
- 수집 범위, 링크 규칙, 제한사항 (핵심 인사이트/실행 필요 없음)
- 월간 집계 방법론 (4~5주 데이터 병합, 중복 제거)
- Tier 1/2/3 분류 기준

---

## 3. 핵심 인사이트 + 실행 필요 블록 규칙

Weekly와 동일한 규칙을 적용하되, Monthly에서는 **월간 추세 기반 인사이트**를 작성한다.

```markdown
### 핵심 인사이트
- [월간 추세 기반 전략적 해석 1 — 주차별 변화 패턴 언급]
- [전략적 해석 2 — MoM 비교 포함]
- [전략적 해석 3 — 중장기 시사점]

### 실행 필요
1. [중장기 실행 지시 — 국가/제품/타임라인 포함]
2. [구체적 실행 지시 — 월간 데이터 기반 근거 제시]
3. [구체적 실행 지시]
```

예외: Appendix A/B, Section 7(차트 갤러리)에는 작성하지 않는다.

---

## 4. 표기 규칙

Weekly Format Spec v2.0의 모든 표기 규칙을 그대로 적용한다.

### 추가 표기 (Monthly 전용)
- 주차 표기: W1, W2, W3, W4 (해당 월의 주 순서)
- MoM 변화율: `+12.5%↑` (증가), `-8.3%↓` (감소), `0.0%→` (변동 없음)
- 추세 아이콘: 📈 (상승 추세), 📉 (하락 추세), ➡️ (횡보)
- 월 표기: `YYYY년 MM월` (한국어), `Month YYYY` (영어)

---

## 5. 콘텐츠 균형 규칙

Weekly의 모든 균형 규칙 + 아래 추가:

### 시간축 균형
- W1~W4 데이터를 **균등하게** 분석에 반영 — 최신 주만 과도하게 반영하지 않음
- MoM 비교 시 **전월 전체 평균** 대비 (특정 주간만 비교 금지)

### 심화 분석 깊이
- Section 4(제품별 Deep Dive)는 **주간 리포트에 없는 새로운 인사이트**를 도출
- 단순 데이터 나열이 아닌, 패턴/상관관계/인과관계 분석을 포함

### 차트 데이터 정합성
- 차트의 데이터와 본문 테이블의 숫자가 **일치**해야 함
- 차트 JSON 데이터 블록의 값은 본문에서 인용한 수치와 동일

---

## 6. 품질 기준

- 파일 크기: **최소 100KB** (120KB+ 권장)
- 16개국 **모두** 각 주요 테이블에 포함 (빠진 국가 없어야 함)
- 모든 테이블 행에 Source 링크 포함 (대표 1건 이상)
- 차트 마커 최소 5개 이상 포함
- 주차별 데이터 최소 3주분 존재 (주간 리포트가 3회 이상 있어야 생성 가능)
- 핵심 인사이트 블록 8개+, 실행 필요 블록 8개+
- Source 링크 20건+
- **제품 균형 체크**: Key Findings 12건 중 TV 외 제품 4건+
- MoM 비교 데이터 포함 (전월 통계 없으면 "N/A" 표기)
- 영어 HTML에서 한글 문자열 0건

---

## 7. Chart.js 데이터 블록 규칙

차트 마커 아래에 JSON 코드블록을 삽입한다. 렌더러(`render_professional_report.mjs`)가 파싱하여 Chart.js canvas로 변환한다.

```markdown
<!-- CHART:monthly_product_trend -->
```json:chart
{
  "type": "line",
  "title": "제품별 4주 시그널 추이",
  "labels": ["W1", "W2", "W3", "W4"],
  "datasets": [
    {"label": "TV", "data": [180, 195, 172, 192], "color": "#003a66"},
    {"label": "Refrigerator", "data": [140, 155, 148, 160], "color": "#0a7ac4"},
    {"label": "Washing Machine", "data": [130, 142, 138, 161], "color": "#2196F3"},
    {"label": "Monitor", "data": [70, 82, 78, 85], "color": "#4CAF50"},
    {"label": "LG gram", "data": [45, 52, 48, 60], "color": "#FF9800"}
  ]
}
```
```

**지원 차트 타입**: `line`, `bar`, `doughnut`, `polarArea`
**필수 필드**: `type`, `title`, `labels`, `datasets`
**datasets 필수 필드**: `label`, `data`, `color`

---

## 8. HTML 시각 디자인 규칙

Weekly의 모든 디자인 규칙을 그대로 적용 + 아래 추가:

- Monthly 리포트 커버: **보라/남색 그라데이션** (Weekly의 파랑 계열과 차별화)
  - `linear-gradient(135deg, #1a0533 0%, #003a66 50%, #0a7ac4 100%)`
- Chart.js 캔버스는 `.chart-container` 클래스로 감싸며, max-width: 800px, 반응형
- 인쇄/PDF 시 Chart.js canvas → 정적 이미지로 대체 (Playwright 캡처)
- Monthly Hub는 별도 탭 또는 섹션으로 Weekly Hub에 통합
