# Global D2C Report Edit Guardrails

아래 규칙은 주간 보고서 편집 시 고정 적용한다.

1. Appendix A/B/C에는 `핵심 인사이트`, `실행 필요`를 작성하지 않는다.
2. HTML 보고서 왼쪽 메뉴(TOC)에서는 `핵심 인사이트`, `실행 필요`를 노출하지 않는다.
3. 목차 섹션(`목차`, `Table of Contents`)은 작성하지 않는다.
4. 용어집 약어는 `MS`, `HS`를 사용하고 `HE`, `H&A`는 사용하지 않는다.
5. 용어 정의는 `MS = Media Entertainment Solution`, `HS = Home appliance solution`으로 고정한다.
6. 국가 표기는 `국기 + 국가명 (+국가코드)` 형식(예: `🇺🇸 미국 (US)`)으로 작성한다.
7. Key Findings 10건 중 **TV 외 제품(냉장고/세탁기/모니터/gram)을 최소 3건** 포함한다.
8. Section 4 Chinese Brand 분석에서 **TV(TCL/Hisense)와 가전(Haier/Midea)을 분리** 분석한다.
9. Tier 3 국가(TW/SG/EG/CL/MX)도 **TV 외 제품 인사이트를 최소 1건** 포함한다.
10. 보고 기간은 **전주 일요일~토요일**(7일 고정)로 작성한다.
11. HTML 시각 규칙: `##` 섹션 제목은 띠 배너(`.section-title`), `### 핵심 인사이트`/`### 실행 필요`는 각각 강조 배너(`.key-insight-banner`/`.action-required-banner`)가 적용되어야 한다.
12. 본문 제목/타이틀은 한글 우선 표기(예: `경영진 요약`, `핵심 경보`, `전주 대비 추이`)로 작성한다.
13. 제목/타이틀의 `16개국` 표현은 `핵심 법인`으로 통일한다.
14. 영어판 리포트(`index_en.html`)는 본문/인용/섹션 제목까지 영어로 작성하고 한글 잔존을 허용하지 않는다.
15. 허브(`hub.html`, `hub_en.html`)의 PDF 링크는 상대경로(`../pdf/...`)로 고정하고 `file:///` 절대경로를 사용하지 않는다.
16. 허브 비교 영역에서는 하단 Week A/B Key Insight 중복 블록을 노출하지 않는다.
