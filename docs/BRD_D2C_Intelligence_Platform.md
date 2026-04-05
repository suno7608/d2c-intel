# D2C Global Market Intelligence Platform — Business Requirements Document (BRD)

**Version**: 1.0  
**Date**: 2026-04-05  
**Author**: D2C Intel Team  
**Status**: Draft  

---

## 1. Executive Summary

### 1.1 목적
LG전자 D2C(Direct-to-Consumer) 글로벌 마켓 인텔리전스 플랫폼을 구축하여, 기존 주간 보고서(Weekly Intelligence Report) 기반의 데이터를 interactive한 웹 대시보드로 전환한다. 사용자가 글로벌 시장 데이터를 쉽게 조회·검색·분석하고, AI 에이전트를 통해 인사이트와 액션을 즉시 얻을 수 있도록 한다.

### 1.2 핵심 가치
- **기존 자산 보존**: 4주차 축적된 Weekly Report 포맷/형식 유지 및 Newsletter 구독 체계 존속
- **접근성 향상**: Vercel 배포를 통한 글로벌 접근, 지역별/제품별 필터링
- **AI 기반 인사이트**: 축적 데이터 기반 D2C Intel Agent가 질의응답 및 분석 리포트 자동 생성
- **실시간 센싱**: Daily NewsClip으로 경쟁사·유통채널·고객 동향 매일 파악

---

## 2. 현재 시스템 (As-Is)

### 2.1 데이터 파이프라인
```
Brave Search API + DuckDuckGo → d2c_search.py → JSONL (주간 ~1,000건)
  → Claude Opus (Report Generation) → Markdown → HTML/PDF
  → Gmail API (Newsletter 발송)
```

### 2.2 현재 데이터 자산
| 항목 | 현황 |
|------|------|
| 수집 주기 | Weekly (매주 일요일 16:00 KST) |
| 커버리지 국가 | 15개국 (US, UK, DE, AU, BR, CA, FR, IT, ES, TH, SA, TR, MX, CL, TW, SG, EG) |
| 제품군 | 5개 (TV, Refrigerator, Washing Machine, Monitor, LG gram) |
| 분석 필라 | 5개 (Consumer Sentiment, Retail Promotions, Price Intelligence, Chinese Brand Threat, Market Signal) |
| 추적 브랜드 | 11개 (LG, Samsung, TCL, Hisense, Haier, Midea, Bosch, Electrolux, Panasonic, Xiaomi, Whirlpool) |
| 축적 데이터 | 4주간 ~4,200건 (3/15, 3/22, 3/29, 4/05) |
| 가격 추적 | 702건 히스토리, 주간 Price Alert 자동 생성 |
| 보고서 | 주간 KO/EN (HTML, PDF, MD), 월간 리포트 |

### 2.3 현재 Newsletter
- Gmail API + Google Sheets 구독자 관리
- 주간 PDF 첨부 + Executive Summary HTML 발송
- `d2c_email_sender.py` → **그대로 유지**

---

## 3. 목표 시스템 (To-Be)

### 3.1 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Vercel App (Next.js)                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Dashboard │  │ Reports  │  │ NewsClip │  │ D2C Intel  │  │
│  │  (Home)   │  │ Viewer   │  │  Daily   │  │   Agent    │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │  Global  │  │ Regional │  │  Search  │                  │
│  │ Overview │  │  Views   │  │ & Filter │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
         │                │               │
         ▼                ▼               ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│ Data Layer  │  │ Brave/DDG    │  │ Claude API   │
│ (JSONL/JSON)│  │ Search API   │  │ (Agent/Report)│
└─────────────┘  └──────────────┘  └──────────────┘
```

### 3.2 배포 환경
| 항목 | 선택 |
|------|------|
| Framework | Next.js 14+ (App Router) |
| 배포 | Vercel |
| 스타일 | Tailwind CSS + shadcn/ui |
| 차트 | Recharts |
| AI Agent | Claude API (Anthropic SDK) |
| 데이터 | GitHub repo JSON/JSONL → API Routes |

---

## 4. 기능 요구사항

### 4.1 Dashboard Home (글로벌 Overview)

**FR-01: Executive Dashboard**
- 최신 주차의 핵심 지표를 한눈에 표시
  - 총 수집량, 국가 수, 제품별 분포 (도넛 차트)
  - 브랜드 점유율 트렌드 (주간 추이 라인 차트)
  - Chinese Brand Threat 수준 (게이지/히트맵)
  - Consumer Negative 신호 카운트 (경고 배지)
  - 가격 변동 알림 Top 5
- 주간 대비 변화율 표시 (↑↓ 지표)

**FR-02: 지역별 Overview (5개 Region)**
| Region | 국가 |
|--------|------|
| 북미 (North America) | US, CA, MX |
| 유럽 (Europe) | UK, DE, FR, ES, IT |
| 중남미 (Latin America) | BR, CL |
| 아시아 (Asia Pacific) | AU, TH, TW, SG |
| 중동/아프리카 (MEA) | SA, EG, TR |

- 지역별 탭/카드로 전환 가능
- 각 지역: 수집 건수, 주요 브랜드 분포, Critical Alert, 가격 변동
- 지역 내 국가별 드릴다운

### 4.2 Weekly Report Viewer

**FR-03: 기존 Weekly Report 열람**
- 기존 HTML 보고서를 iframe 또는 렌더링하여 그대로 제공
- 주차별 선택 (드롭다운/타임라인)
- KO/EN 전환 토글
- PDF 다운로드 링크
- Executive Summary 하이라이트 카드

**FR-04: Report Archive & Navigation**
- 전체 주차 목록 (manifest.json 기반)
- 주차별 메타데이터 미리보기 (critical countries, key insights)
- 월간 리포트 별도 섹션

### 4.3 Newsletter 구독

**FR-05: Newsletter 구독 (기존 유지)**
- 기존 `d2c_email_sender.py` + Google Sheets 구독자 관리 그대로 사용
- 웹에서 구독 신청 폼 → Google Sheets에 이메일 추가
- 주간 보고서 + Daily NewsClip 구독 옵션 분리

### 4.4 Daily NewsClip (신규)

**FR-06: Daily NewsClip 수집**
- 매일 자동 수집 (GitHub Actions cron, 매일 09:00 KST)
- 수집 대상:
  - **경쟁사 소식**: Samsung, TCL, Hisense, Haier, Midea 신제품/전략/파트너십
  - **유통 채널 마케팅**: Best Buy, Amazon, MediaMarkt 등 프로모션/딜
  - **고객 반응**: Reddit, 커뮤니티 신규 이슈
- Brave Search API 활용 (일간 쿼리, freshness: "pd")
- 지역별 5개 Region으로 분류

**FR-07: NewsClip 대시보드**
- AI Trend Hub 스타일의 뉴스 피드 UI
- 카테고리 필터: 경쟁사 | 유통채널 | 고객반응
- 지역별 필터
- 중요도 태깅 (Critical / Warning / Normal)
- 클릭 → 원문 소스 URL 이동

**FR-08: Daily NewsClip Newsletter**
- 매일 오전 발송 (기존 Gmail API 인프라 활용)
- 3개 섹션: 경쟁사 동향 / 유통 프로모션 / 고객 반응
- 지역별 그룹핑
- 구독자별 관심 지역 설정 가능

### 4.5 Search & Discovery

**FR-09: 통합 검색**
- 전체 축적 데이터 (모든 주차 JSONL) 대상 풀텍스트 검색
- 필터: 기간 / 국가 / 제품 / 브랜드 / Pillar / Signal Type
- 검색 결과: 카드형 리스트 + 원문 스니펫 + 소스 링크
- 최근 검색어 / 추천 키워드

**FR-10: 데이터 탐색기 (Explorer)**
- 국가 × 제품 × 브랜드 매트릭스 히트맵
- 시계열 트렌드 차트 (주간 추이)
- 가격 히스토리 모델별 추적 차트
- 필터 조합으로 맞춤 분석 뷰 생성

### 4.6 D2C Intel Agent (AI Assistant)

**FR-11: 대화형 AI 에이전트**
- 채팅 인터페이스 (웹 우측 패널 또는 전체 페이지)
- 축적된 모든 주간 데이터를 컨텍스트로 활용
- Claude API (Anthropic SDK) 기반
- 질의 예시:
  - "지난 4주간 독일에서 TCL의 가격 전략 변화를 분석해줘"
  - "미국 냉장고 시장에서 LG의 소비자 불만 트렌드는?"
  - "유럽 지역 중국 브랜드 위협 수준을 비교해줘"
  - "다음 주 프로모션 전략을 제안해줘"

**FR-12: AI 분석 리포트 생성**
- 사용자가 조건을 지정하면 맞춤 분석 리포트 자동 생성
  - 조건: 기간, 국가, 제품, 분석 관점
- 생성 형식: 마크다운 → 다운로드 가능 (PDF/HTML)
- **Insight + Action Required** 구조로 출력
- 리포트 히스토리 저장

### 4.7 데이터 중심 구조 (고객·유통·경쟁사)

**FR-13: 3축 데이터 뷰**

| 축 | 데이터 소스 | 대시보드 요소 |
|---|---|---|
| **고객 (Consumer)** | consumer_sentiment, consumer_complaint, community_reaction, expert_review | 감성 트렌드, 불만 히트맵, 커뮤니티 버즈, 리뷰 점수 추이 |
| **유통 채널 (Retail)** | retail_channel_promotion, promo, price_discount | 프로모션 캘린더, 딜 히트맵, 채널별 가격 비교 |
| **경쟁사 (Competitor)** | chinese_brand_threat, competitive_move, pricing_comparison | 브랜드별 점유율 추이, 가격 포지셔닝 차트, 위협 수준 게이지 |

- 각 축별 전용 대시보드 페이지
- 3축 종합 요약을 Home Dashboard에 표시

---

## 5. 비기능 요구사항

### 5.1 성능
- First Contentful Paint < 1.5s
- 데이터 로딩 (JSONL 파싱) < 3s
- AI Agent 응답 < 15s (스트리밍)

### 5.2 접근성
- 모바일 반응형 (태블릿, 모바일 대응)
- KO/EN 다국어 지원
- 다크 모드 지원

### 5.3 보안
- Vercel 인증 (필요시 Vercel Auth 또는 간단한 비밀번호 게이트)
- API Key 서버사이드 관리 (Claude API, Brave API)
- 데이터 접근 제어 (Confidential 리포트 보호)

### 5.4 배포
- **Vercel** 배포 (vercel.app 도메인)
- GitHub 연동 자동 배포 (push → deploy)
- 환경 변수: ANTHROPIC_API_KEY, BRAVE_API_KEY, 기타

---

## 6. 정보 아키텍처 (IA)

```
/                          → Dashboard Home (Executive Overview)
├── /reports               → Weekly Report Viewer (주차 목록)
│   ├── /reports/[date]    → 특정 주차 보고서 (KO/EN, PDF)
│   └── /reports/monthly   → 월간 리포트
├── /regions               → 지역별 Overview
│   ├── /regions/na        → 북미
│   ├── /regions/eu        → 유럽
│   ├── /regions/latam     → 중남미
│   ├── /regions/apac      → 아시아
│   └── /regions/mea       → 중동/아프리카
├── /newsclip              → Daily NewsClip (뉴스 피드)
│   └── /newsclip/[date]   → 특정 일자 뉴스
├── /explore               → 데이터 탐색기
│   ├── /explore/consumer  → 고객 축
│   ├── /explore/retail    → 유통 축
│   └── /explore/competitor → 경쟁사 축
├── /search                → 통합 검색
├── /agent                 → D2C Intel Agent (AI Chat)
├── /subscribe             → Newsletter 구독
└── /settings              → 설정 (언어, 지역 관심 설정)
```

---

## 7. 데이터 모델

### 7.1 기존 데이터 (유지)
```typescript
// Weekly Raw Record (openclaw_YYYY-MM-DD.jsonl)
interface RawRecord {
  country: string;          // "US", "DE", "TR", ...
  product: string;          // "TV", "Refrigerator", ...
  pillar: string;           // "Consumer Sentiment", ...
  brand: string;            // "LG", "Samsung", "Unknown"
  signal_type: string;      // "promo", "competitive_move", ...
  value: string;            // 제목
  currency: string;         // "USD", "EUR", ...
  price_value: string;      // "1,399.99"
  discount: string;         // "53%"
  rating: string;           // "4.5/5"
  quote_original: string;   // 스니펫 (500자)
  source_url: string;
  source: string;           // 도메인
  collected_at: string;     // ISO 8601
  confidence: string;       // "high" | "medium"
}

// Weekly Stats (data/weekly_stats/YYYY-MM-DD.json)
interface WeeklyStats {
  date: string;
  total_records: number;
  countries_count: number;
  countries: Record<string, number>;
  products: Record<string, number>;
  brands: Record<string, number>;
  pillars: Record<string, number>;
  confidence: Record<string, number>;
  tv_ratio_pct: number;
  chinese_brand_total: number;
  chinese_by_country: Record<string, number>;
  chinese_by_product: Record<string, number>;
  consumer_negative_count: number;
  lg_promo_count: number;
}

// Price Alert (data/price_history/price_alerts_YYYY-MM-DD.json)
interface PriceAlert {
  price_key: string;
  brand: string;
  product: string;
  model: string;
  country: string;
  currency: string;
  prev_price: number;
  new_price: number;
  change_pct: number;
  direction: "drop" | "increase";
  source_url: string;
}
```

### 7.2 신규 데이터

```typescript
// Daily NewsClip Record (data/newsclip/YYYY-MM-DD.jsonl)
interface NewsClipRecord {
  date: string;
  category: "competitor" | "retail_channel" | "consumer_reaction";
  region: "na" | "eu" | "latam" | "apac" | "mea";
  country: string;
  brand: string;
  title: string;
  snippet: string;
  source_url: string;
  source: string;
  severity: "critical" | "warning" | "normal";
  collected_at: string;
}
```

---

## 8. 마일스톤

| Phase | 기간 | 범위 |
|-------|------|------|
| **Phase 1: Foundation** | Week 1-2 | Next.js 프로젝트 셋업, Dashboard Home, Weekly Report Viewer, 지역별 뷰, Vercel 배포 |
| **Phase 2: Intelligence** | Week 3-4 | 통합 검색, 데이터 탐색기 (3축 뷰), 가격 추적 차트 |
| **Phase 3: AI Agent** | Week 5-6 | D2C Intel Agent (Claude API Chat), AI 분석 리포트 생성 |
| **Phase 4: NewsClip** | Week 7-8 | Daily 수집 파이프라인, NewsClip 피드 UI, Daily Newsletter |
| **Phase 5: Polish** | Week 9-10 | 모바일 최적화, 다크 모드, 성능 튜닝, UAT |

---

## 9. 기술 스택

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14+ (App Router, RSC) |
| UI | Tailwind CSS + shadcn/ui |
| Charts | Recharts |
| AI Agent | Anthropic Claude API (claude-sonnet-4-6) |
| Search | Client-side JSONL indexing (Fuse.js) |
| Deploy | Vercel |
| Data Pipeline | GitHub Actions (cron) + Brave Search API |
| Newsletter | Gmail API + Google Sheets (기존 유지) |
| Auth | Vercel Auth / 간단한 비밀번호 게이트 |

---

## 10. 리스크 및 완화

| 리스크 | 영향 | 완화 방안 |
|--------|------|----------|
| JSONL 데이터 크기 증가 (월 4,000건+) | 로딩 속도 저하 | ISR(Incremental Static Regeneration) + JSON 사전 집계 |
| Claude API 비용 (Agent 질의) | 운영 비용 증가 | Sonnet 사용, 응답 캐싱, 일일 한도 설정 |
| Daily NewsClip API 호출량 | Brave API 한도 초과 | DDG 보조 + 쿼리 최적화 + 캐싱 |
| 기밀 데이터 외부 노출 | 보안 | Vercel Auth + 접근 제어 |

---

## 11. 성공 지표

| KPI | 목표 |
|-----|------|
| Weekly Report 조회율 | 기존 대비 3배 증가 |
| 평균 체류 시간 | > 5분/세션 |
| AI Agent 질의 | > 20건/주 |
| Daily NewsClip 구독자 | > 50명 (3개월 내) |
| 데이터 기반 의사결정 | Executive Action Item 실행율 70%+ |

---

## Appendix A: 지역 분류 매핑

| Region | Code | 국가 목록 |
|--------|------|----------|
| 북미 (North America) | `na` | US 🇺🇸, CA 🇨🇦, MX 🇲🇽 |
| 유럽 (Europe) | `eu` | UK 🇬🇧, DE 🇩🇪, FR 🇫🇷, ES 🇪🇸, IT 🇮🇹 |
| 중남미 (Latin America) | `latam` | BR 🇧🇷, CL 🇨🇱 |
| 아시아 (Asia Pacific) | `apac` | AU 🇦🇺, TH 🇹🇭, TW 🇹🇼, SG 🇸🇬 |
| 중동/아프리카 (MEA) | `mea` | SA 🇸🇦, EG 🇪🇬, TR 🇹🇷 |

## Appendix B: 기존 Weekly Report 포맷 (유지)
- Executive Summary (Key Insights 3개 + Action Required 3개)
- Key Findings 테이블 (10개 항목, Severity 태깅)
- Key Metrics 주간 비교 테이블
- Action Items 테이블 (P1/P2/P3 우선순위)
- Critical Alerts (국가별 Alert Map)
- 5개 Pillar별 상세 분석
- 17개국 개별 국가 분석
