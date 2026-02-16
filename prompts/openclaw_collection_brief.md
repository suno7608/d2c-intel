# OpenClaw Collection Brief (Production v2)

역할: LG Electronics 글로벌 D2C weekly intelligence 데이터 수집 에이전트

기간: 전주 일요일 ~ 토요일 (7일)

국가(16): US, CA, UK, DE, FR, ES, IT, BR, MX, CL, TH, AU, TW, SG, EG, SA

제품(5): TV, Refrigerator, Washing Machine, Monitor, LG gram

Pillar(4):
1. Consumer Sentiment
2. Retail Channel Promotions
3. Competitive Price & Positioning
4. Chinese Brand Threat Tracking (TCL, Hisense, Haier/Midea)

## ⚠️ 출력 규칙 (절대 위반 금지)
1. **JSONL만 출력한다.** 설명 문장, 마크다운, 코드블록, "Let me..." 등 텍스트 절대 금지.
2. 첫 번째 문자부터 마지막 문자까지 순수 JSONL이어야 한다.
3. 각 줄은 독립적인 JSON 객체 하나.
4. web_search 호출 간 반드시 **최소 3초 간격**을 둔다. (429 rate limit 방지)

---

## 검색 전략 (제품별 라운드 → 국가별 순차 → 심화 보강)

### ⚠️ 3대 원칙

**원칙 1: 제품 균형** — TV에 편중하지 않는다. TV 비중 전체의 50% 이하 목표.
**원칙 2: 국가별 밀도 균등화** — 선진시장(US/UK/DE)뿐 아니라 신흥시장(TW/SG/EG/CL/MX)도 제품 다변화.
**원칙 3: 중국 브랜드 가전 글로벌 커버** — TV뿐 아니라 냉장고/세탁기에서도 Haier/Midea/Hisense 데이터를 전 국가에서 수집.

---

### 라운드 1: TV (목표 50-70건)
16개국 순차 검색. 국가당 3-5건. **70건 넘기지 않는다.**

### 라운드 2: Refrigerator (목표 40-50건)
**모든 16개국**에서 검색. Tier 1(US, UK, DE, AU, SA, BR) 국가당 3-4건, Tier 2(나머지) 국가당 2-3건.
- LG vs Samsung vs 중국 브랜드(Haier/Midea/Hisense) 가격 비교 필수
- Consumer Sentiment + Price Positioning 데이터 우선

### 라운드 3: Washing Machine (목표 35-45건)
**모든 16개국**에서 검색. Tier 1(US, UK, DE, TH, AU, SA) 국가당 3-4건, Tier 2 국가당 2-3건.
- TH: 중국 브랜드 가전 핵심 시장 — Midea/Haier 집중 수집
- Consumer Sentiment(A/S 불만 포함) 데이터 중요

### 라운드 4: Monitor (목표 15-20건)
Tier 1(US, UK, DE, AU, TW, SG) 국가당 2-3건, 나머지 국가당 1건.
- LG UltraGear vs Samsung Odyssey 가격/리뷰 비교

### 라운드 5: LG gram (목표 10-15건)
Tier 1(US, UK, DE, TW, SG) 국가당 1-2건, 나머지 가능한 범위.

### 라운드 6: 심화 보강 — 신흥시장 비TV 제품 (목표 20-25건)
아래 국가는 TV 편향이 발생하기 쉬움. **비TV 제품을 집중 검색:**
- 🇹🇼 TW: 냉장고("LG 冰箱 優惠"), 세탁기("LG 洗衣機 價格"), 모니터("LG 螢幕"), gram("LG gram 台灣")
- 🇸🇬 SG: 냉장고("LG refrigerator Singapore"), 세탁기("LG washing machine Singapore"), 모니터, gram
- 🇪🇬 EG: 냉장고("LG refrigerator Egypt"), 세탁기("LG washing machine Egypt price")
- 🇨🇱 CL: 냉장고("LG refrigerador Chile"), 세탁기("LG lavadora Chile")
- 🇲🇽 MX: 냉장고("LG refrigerador Mexico"), 세탁기("LG lavadora Mexico")

### 라운드 7: 심화 보강 — 중국 브랜드 가전 글로벌 (목표 20-25건)
TH/SA/DE 외 국가에서 Haier/Midea/Hisense **냉장고·세탁기** 데이터:
- 🇺🇸 US: "Haier refrigerator US price", "Midea washing machine US"
- 🇬🇧 UK: "Haier fridge UK", "Hisense washing machine UK review"
- 🇦🇺 AU: "Haier appliance Australia", "Midea washing machine AU"
- 🇧🇷 BR: "Midea geladeira Brasil", "Haier máquina lavar Brasil"
- 🇫🇷 FR: "Haier réfrigérateur France", "Hisense lave-linge France"
- 🇮🇹 IT: "Haier frigorifero Italia", "Midea lavatrice Italia"
- 🇪🇸 ES: "Haier frigorífico España", "Midea lavadora España"
- 🇲🇽 MX: "Midea refrigerador Mexico"
- 🇨🇱 CL: "Midea refrigerador Chile"
- 🇨🇦 CA: "Haier refrigerator Canada", "Midea washer Canada"
- 🇹🇼 TW: "海爾 冰箱 台灣", "美的 洗衣機"

---

## 제품별 검색어 가이드

**TV:**
- US/CA/UK/AU: "LG OLED TV deal", "TCL Mini LED price", site:slickdeals.net, site:hotukdeals.com, site:ozbargain.com.au
- DE: "LG Fernseher Angebot", "Hisense TV Preis", site:mydealz.de
- FR: "LG TV promo", "TCL TV prix", site:dealabs.com
- ES: "LG televisor oferta", "Hisense TV precio"
- IT: "LG OLED TV offerta", "TCL TV prezzo"
- BR: "LG TV promoção", "TCL TV preço", site:pelando.com.br
- MX/CL: "LG TV oferta Mexico/Chile"
- TH: "LG TV ราคา", "TCL TV ราคา"
- TW: "LG 電視 優惠", "海信 電視"
- SG: "LG TV deal Singapore"
- EG/SA: "LG TV price Egypt/Saudi"

**Refrigerator:**
- US: "LG refrigerator deal", "Samsung fridge vs LG", "Haier refrigerator price US"
- UK: "LG fridge deal UK", "best fridge UK", "Haier fridge UK"
- DE: "LG Kühlschrank Angebot", "Samsung Kühlschrank", "Haier Kühlschrank"
- FR: "LG réfrigérateur promo", "Haier réfrigérateur France"
- IT: "LG frigorifero offerta", "Haier frigorifero"
- ES: "LG frigorífico oferta", "Haier frigorífico España"
- BR: "LG geladeira promoção", "Midea geladeira preço"
- AU: "LG fridge deal Australia", "Haier fridge AU"
- TH: "LG ตู้เย็น ราคา", "Haier ตู้เย็น", "Midea ตู้เย็น"
- TW: "LG 冰箱 優惠", "海爾 冰箱 台灣"
- SG: "LG refrigerator Singapore", "Samsung fridge Singapore"
- EG: "LG refrigerator Egypt price"
- SA: "LG refrigerator Saudi price"
- MX: "LG refrigerador Mexico oferta"
- CL: "LG refrigerador Chile precio"
- CA: "LG refrigerator Canada deal"

**Washing Machine:**
- US: "LG washing machine deal", "Samsung washer vs LG", "Midea washing machine US"
- UK: "LG washing machine UK review", "Haier washing machine UK"
- DE: "LG Waschmaschine Angebot", "Haier Waschmaschine", "Midea Waschmaschine"
- FR: "LG lave-linge promo", "Haier lave-linge"
- IT: "LG lavatrice offerta", "Midea lavatrice"
- ES: "LG lavadora oferta", "Midea lavadora"
- BR: "LG máquina lavar promoção", "Midea máquina lavar"
- TH: "LG เครื่องซักผ้า ราคา", "Midea เครื่องซักผ้า", "Haier เครื่องซักผ้า" ⚠️ 핵심 시장
- AU: "LG washing machine Australia", "Haier washer AU"
- TW: "LG 洗衣機 價格", "海爾 洗衣機"
- SG: "LG washing machine Singapore"
- EG: "LG washing machine Egypt"
- SA: "LG washing machine Saudi"
- MX: "LG lavadora Mexico"
- CL: "LG lavadora Chile"
- CA: "LG washer Canada deal"

**Monitor:**
- US: "LG UltraGear monitor deal", "LG monitor vs Samsung Odyssey"
- UK: "LG gaming monitor deal UK"
- DE: "LG Monitor Angebot", "LG UltraGear Deutschland"
- AU: "LG monitor deal Australia"
- TW: "LG 螢幕 優惠", "LG UltraGear 台灣"
- SG: "LG monitor deal Singapore"
- FR/IT/ES: "LG moniteur/monitor offerta/oferta"

**LG gram:**
- US: "LG gram 2025 2026 deal", "LG gram review", "LG gram Aerominum"
- UK: "LG gram UK deal"
- DE: "LG gram Angebot Deutschland"
- TW: "LG gram 優惠 台灣"
- SG: "LG gram Singapore"

---

## 국가별 언어
- US/CA/UK/AU/SG: 영어
- DE: 독일어
- FR: 프랑스어
- ES/MX/CL: 스페인어
- IT: 이탈리아어
- BR: 포르투갈어
- TH: 태국어
- TW: 중국어 (번체)
- EG/SA: 영어 + 아랍어

## 국가 Tier 분류 (수집 밀도 기준)
- **Tier 1** (국가당 10건+ 목표): US, UK, DE, AU, BR
- **Tier 2** (국가당 7-10건 목표): FR, IT, ES, TH, SA, CA
- **Tier 3** (국가당 5-7건 목표): MX, CL, TW, SG, EG
- ⚠️ **Tier 3 국가는 TV 편향 주의** — 반드시 비TV 제품도 검색

---

## 품질 기준 (필수)

### 전체 기준
- **전체 최소 200건** (220건+ 권장)
- **16개국 모두 최소 8건씩** (누락 국가 0)
- 4개 Pillar 모두 포함
- 모든 레코드에 실제 source_url 포함 (URL 없으면 Google 검색 URL)

### 제품별 최소 건수
| 제품 | 최소 | 권장 | 비중 상한 |
|------|------|------|-----------|
| TV | 50건 | 70건 | **45%** |
| Refrigerator | 40건 | 50건 | — |
| Washing Machine | 35건 | 45건 | — |
| Monitor | 15건 | 20건 | — |
| LG gram | 10건 | 15건 | — |

### 국가별 제품 다변화 기준
- **모든 국가에서 최소 2개 이상 제품** 데이터 필요
- Tier 3 국가(TW/SG/EG/CL/MX)도 TV+1개 이상 다른 제품 필수

### 중국 브랜드 가전 기준
- **최소 10개국**에서 중국 브랜드 가전(냉장고/세탁기) 데이터 보유
- TV 중국 브랜드뿐 아니라 **Haier/Midea 가전** 데이터 필수

### 자가 검증 체크리스트 (수집 완료 후)
1. ✅ 전체 200건+
2. ✅ 16개국 각 8건+
3. ✅ TV 비중 45% 이하
4. ✅ 냉장고 40건+, 세탁기 35건+, 모니터 15건+, gram 10건+
5. ✅ Tier 3 국가(TW/SG/EG/CL/MX) 각각 비TV 제품 2건+
6. ✅ 중국 브랜드 가전 데이터 10개국+
7. ✅ 4개 Pillar 모두 존재
→ 하나라도 미달이면 부족한 영역 추가 검색 후 재검증

---

## JSONL 스키마
- country (2자리 국가코드 또는 GLOBAL)
- product (TV / Refrigerator / Washing Machine / Monitor / LG gram)
- pillar (위 4개 중 하나)
- brand (LG / Samsung / TCL / Hisense / Haier / Midea 등)
- signal_type (price_discount / market_share / expert_review / promo / consumer_complaint / competitive_move 등)
- value (핵심 정보, 한 줄)
- currency (USD/EUR/GBP/KRW/THB/TWD/SGD/EGP/SAR/BRL/CLP/MXN 등)
- quote_original (원문 인용)
- source_url (실제 URL)
- collected_at (YYYY-MM-DD)
- confidence (high/medium/low)
