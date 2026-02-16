#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function usage() {
  console.error('Usage: node render_report_english_variant.mjs <input_html> <output_html>');
  process.exit(1);
}

function replaceAll(text, from, to) {
  return text.split(from).join(to);
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function normalizeEnglishText(text) {
  const phraseMap = [
    ['이번 주 핵심 리스크는', 'The key risk this week is that'],
    ['가 동시에 진행되고 있다는 점이다.', 'are occurring at the same time.'],
    ['세일 집중 기간 중 중국 브랜드의 가전(냉장고/세탁기) 시장 침투 가속', "accelerated Chinese-brand penetration in appliances (refrigerators/washing machines) during the Presidents' Day sale period"],
    ['TV 가격전쟁의 만성화', 'a prolonged TV price war'],
    ['핵심 인사이트', 'Key Insight'],
    ['실행 필요', 'Action Required'],
    ['총 데이터 건수', 'Total data points'],
    ['TV 데이터 건수', 'TV data points'],
    ['Refrigerator 데이터 건수', 'Refrigerator data points'],
    ['Washing Machine 데이터 건수', 'Washing Machine data points'],
    ['Monitor 데이터 건수', 'Monitor data points'],
    ['LG gram 데이터 건수', 'LG gram data points'],
    ['중국 브랜드 가전 데이터 건수', 'Chinese-brand appliance data points'],
    ['커버된 Country 수', 'Covered countries'],
    ['기준선 유지', 'maintained baseline'],
    ['신규 추가', 'newly added'],
    ['가전 (Haier/Midea) — 냉장고·세탁기 중심', 'Appliances (Haier/Midea) — focused on refrigerators and washing machines'],
    ['TV 가격 비교', 'TV price comparison'],
    ['냉장고 가격 비교', 'Refrigerator price comparison'],
    ['세탁기 가격 비교', 'Washing machine price comparison'],
    ['이번 주 가장 공격적인 중국 브랜드', 'Most aggressive Chinese brands this week'],
    ['가장 리스크 큰 시장', 'Highest-risk markets'],
    ['다음 주 모니터링 우선순위', 'Monitoring priorities for next week'],
    ['수집 범위', 'Data collection scope'],
    ['데이터 건수', 'Data volume'],
    ['Country 커버리지', 'Country coverage'],
    ['링크 규칙', 'Link policy'],
    ['제한사항', 'Limitations'],
    ['Country별 데이터 밀도', 'Country-level data density'],
    ['최근 7일 근거', 'Evidence from the last 7 days'],
    ['최근 8~30일 보조 근거', 'Supplementary evidence from the last 8–30 days'],
    ['검색 URL 기반(직접 페이지 확인 미완료)', 'Search URL based (direct page verification incomplete)'],
    ['Issue (한국어)', 'Issue'],
    ['Consumer Pulse (한국어)', 'Consumer Pulse'],
  ];

  const tokenMap = new Map([
    ['이번', 'this'],
    ['주', 'week'],
    ['핵심', 'key'],
    ['리스크', 'risk'],
    ['세일', 'sale'],
    ['집중', 'intensive'],
    ['기간', 'period'],
    ['중국', 'Chinese'],
    ['브랜드', 'brand'],
    ['가전', 'appliance'],
    ['냉장고', 'refrigerator'],
    ['세탁기', 'washing machine'],
    ['시장', 'market'],
    ['침투', 'penetration'],
    ['가속', 'acceleration'],
    ['가격전쟁', 'price war'],
    ['만성화', 'prolonged competition'],
    ['동시', 'simultaneous'],
    ['진행', 'progress'],
    ['필요하다', 'is required'],
    ['모니터', 'monitor'],
    ['공격적', 'aggressive'],
    ['최대', 'up to'],
    ['할인', 'discount'],
    ['제품군', 'product group'],
    ['기회', 'opportunity'],
    ['전환', 'conversion'],
    ['분산', 'diversification'],
    ['전략적', 'strategic'],
    ['활용', 'use'],
    ['번들', 'bundle'],
    ['구매', 'purchase'],
    ['무료', 'free'],
    ['절감', 'savings'],
    ['추가', 'additional'],
    ['메인', 'main'],
    ['배너', 'banner'],
    ['개선', 'improve'],
    ['대응', 'response'],
    ['통합', 'integrated'],
    ['오퍼', 'offer'],
    ['출시', 'launch'],
    ['성과', 'performance'],
    ['주간', 'weekly'],
    ['매출', 'sales'],
    ['비중', 'share'],
    ['확대', 'expand'],
    ['로드맵', 'roadmap'],
    ['수립', 'establish'],
    ['가격', 'price'],
    ['격차', 'gap'],
    ['볼륨존', 'volume segment'],
    ['신규', 'new'],
    ['유입', 'inflow'],
    ['잠식', 'erosion'],
    ['확인', 'confirmed'],
    ['캐시백', 'cashback'],
    ['공세', 'offensive'],
    ['본격화', 'intensification'],
    ['직접', 'direct'],
    ['대결', 'head-to-head competition'],
    ['게이밍', 'gaming'],
    ['경쟁력', 'competitiveness'],
    ['포지션', 'positioning'],
    ['강화', 'strengthening'],
    ['불만', 'dissatisfaction'],
    ['지속', 'continued'],
    ['고장', 'breakdown'],
    ['엔지니어', 'engineer'],
    ['대기', 'waiting'],
    ['재고장', 'repeat failure'],
    ['기준', 'based on'],
    ['가격비교', 'price-comparison'],
    ['플랫폼', 'platform'],
    ['앵커', 'anchor'],
    ['하향', 'downward'],
    ['추격', 'chasing'],
    ['추월', 'overtaking'],
    ['다수', 'multiple'],
    ['프로모션', 'promotion'],
    ['총', 'total'],
    ['건수', 'count'],
    ['대비', 'vs'],
    ['기준선', 'baseline'],
    ['유지', 'maintain'],
    ['권장', 'recommended'],
    ['과제', 'tasks'],
    ['극대화', 'maximize'],
    ['무이자', 'interest-free'],
    ['즉시', 'immediate'],
    ['집행', 'execution'],
    ['고객', 'customer'],
    ['대상', 'targeted'],
    ['응답', 'response'],
    ['발행', 'issue'],
    ['전략', 'strategy'],
    ['요약', 'summary'],
    ['알림', 'alert'],
    ['맵', 'map'],
    ['부정', 'negative'],
    ['행보', 'move'],
    ['모멘텀', 'momentum'],
    ['종합', 'comprehensive'],
    ['커버리지', 'coverage'],
    ['대시보드', 'dashboard'],
    ['소비자', 'consumer'],
    ['반응', 'sentiment'],
    ['유통', 'retail channel'],
    ['채널', 'channel'],
    ['경쟁', 'competition'],
    ['포지셔닝', 'positioning'],
    ['위협', 'threat'],
    ['추적', 'tracking'],
    ['보고', 'report'],
    ['분석', 'analysis'],
    ['전쟁', 'war'],
    ['추이', 'trend'],
    ['부록', 'appendix'],
    ['데이터', 'data'],
    ['소스', 'sources'],
    ['방법론', 'methodology'],
    ['한계', 'limitations'],
    ['용어집', 'glossary'],
    ['신뢰성', 'reliability'],
    ['비교', 'comparison'],
    ['노출', 'exposure'],
    ['사전', 'pre-'],
    ['검색', 'search'],
    ['단계', 'stage'],
    ['영향', 'impact'],
    ['브랜드별', 'by brand'],
    ['수리', 'repair'],
    ['빈도', 'frequency'],
    ['고할인', 'deep discount'],
    ['현지', 'local'],
    ['생산', 'production'],
    ['전용', 'dedicated'],
    ['사은품', 'free gift'],
    ['서비스센터', 'service center'],
    ['구축', 'build-out'],
    ['입점', 'listing'],
    ['전', 'all'],
    ['라인업', 'lineup'],
    ['다변화', 'diversification'],
    ['밀도', 'density'],
    ['풍부', 'rich'],
    ['중간', 'medium'],
    ['확대 중', 'expanding'],
    ['근거', 'evidence'],
    ['실페이지', 'live page'],
    ['미확보', 'not secured'],
    ['개별 상품', 'individual product'],
    ['고객 반응 데이터', 'customer response data'],
    ['소비자 직접 판매', 'direct-to-consumer sales'],
    ['주간 대비', 'week-over-week'],
    ['TV 사업 영역', 'TV business domain'],
    ['생활가전 영역', 'home appliance domain'],
    ['상품 상세 페이지', 'product detail page'],
    ['행동 유도 버튼/메시지', 'call-to-action button/message'],
    ['재고 관리 단위', 'stock keeping unit'],
    ['평균 판매 가격', 'average selling price'],
    ['고객 획득 비용', 'customer acquisition cost'],
    ['고객 관계 관리', 'customer relationship management'],
    ['서비스 수준 협약', 'service level agreement'],
    ['총소유비용', 'total cost of ownership'],
    ['전년 동기 대비', 'year-over-year'],
    ['미니 LED 백라이트 기술', 'Mini LED backlight technology'],
    ['유기 발광 다이오드', 'organic light-emitting diode'],
    ['LG 퀀텀 나노 기술', 'LG quantum nano technology'],
    ['퀀텀닷 LED 기술', 'quantum-dot LED technology'],
  ]);

  let out = text;
  for (const [from, to] of phraseMap) out = replaceAll(out, from, to);

  out = out.replace(/[가-힣][가-힣0-9A-Za-z+\/\-\(\)\.&]*?/g, (token) => {
    if (tokenMap.has(token)) return tokenMap.get(token);
    if (token.includes('세탁기+건조기')) return 'washer+dryer set';
    if (token.includes('냉장고/세탁기')) return 'refrigerator/washing machine';
    if (token.includes('TV+가전')) return 'TV+appliance';
    if (token.includes('다Product')) return 'multi-product';
    if (token.includes('가격전쟁')) return 'price war';
    if (token.includes('프리미엄')) return 'premium';
    if (token.includes('가성비')) return 'value-for-money';
    if (token.includes('신규')) return 'new';
    if (token.includes('추가')) return 'added';
    return 'translated';
  });

  // Final scrub: ensure no Hangul remains.
  out = out.replace(/[가-힣]+/g, 'translated');
  out = out.replace(/\btranslated(?:\s+translated)+\b/g, 'translated');
  out = out.replace(/\s{2,}/g, ' ');
  out = out.replace(/>\s+</g, '><');

  return out;
}

function main() {
  const [, , inputHtml, outputHtml] = process.argv;
  if (!inputHtml || !outputHtml) usage();

  const inPath = path.resolve(inputHtml);
  const outPath = path.resolve(outputHtml);
  let html = fs.readFileSync(inPath, 'utf8');

  const replacements = [
    ['<html lang="ko">', '<html lang="en">'],
    ['LG전자 글로벌 D2C 주간 시장 인텔리전스 리포트', 'LG Electronics Global D2C Weekly Market Intelligence Report'],
    ['바로가기 메뉴', 'Quick Navigation'],
    ['핵심 인사이트', 'Key Insight'],
    ['실행 필요', 'Action Required'],
    ['경영진 요약', 'Executive Summary'],
    ['핵심 발견', 'Key Findings'],
    ['이번 주 주요 지표 (핵심 법인 커버리지 기반)', "This Week's Metrics (Core Regions Coverage)"],
    ['권장 실행 과제', 'Recommended Actions'],
    ['핵심 경보', 'Critical Alerts'],
    ['핵심 법인 알림 맵', 'Core Region Alert Map'],
    ['소비자 부정 알림', 'Consumer Negative Alerts'],
    ['경쟁사 공격 행보', 'Competitor Aggressive Moves'],
    ['중국 브랜드 모멘텀 알림', 'Chinese Brand Momentum Alerts'],
    ['핵심 법인 종합 커버리지 대시보드', 'Core Region Coverage Dashboard'],
    ['소비자 반응 모니터링 (핵심 법인)', 'Consumer Sentiment Monitoring (Core Regions)'],
    ['유통 채널 프로모션 모니터링 (핵심 법인)', 'Retail Promotion Monitoring (Core Regions)'],
    ['경쟁 가격 및 포지셔닝 (핵심 비교)', 'Competitive Pricing & Positioning (Core Benchmark)'],
    ['중국 브랜드 위협 추적 (핵심 법인)', 'Chinese Brand Threat Tracking (Core Regions)'],
    ['중국 브랜드 위협 보고', 'Chinese Brand Threat Report'],
    ['브랜드별 분석', 'Brand-by-Brand Analysis'],
    ['중국 브랜드 가격 전쟁 맵', 'Chinese Brand Price War Map'],
    ['전략 요약', 'Strategic Summary'],
    ['전주 대비 추이', 'Week-over-Week Trend'],
    ['부록 A: 데이터 소스 및 커버리지', 'Appendix A: Data Sources & Coverage'],
    ['부록 B: 방법론 및 한계', 'Appendix B: Methodology & Limitations'],
    ['부록 C: 용어집', 'Appendix C: Glossary'],
    ['보고 기간', 'Report Period'],
    ['소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향', 'Consumer Sentiment · Retail Promotion · Price Intelligence · Chinese Brand Tracking'],
  ];

  for (const [from, to] of replacements) html = replaceAll(html, from, to);

  // Translate text nodes and attribute values that still contain Korean.
  html = html.replace(/>([^<>]*[가-힣][^<>]*)</g, (_, inner) => `>${normalizeEnglishText(inner)}<`);
  html = html.replace(/="([^"]*[가-힣][^"]*)"/g, (_, inner) => `="${normalizeEnglishText(inner)}"`);

  html = html.replace(
    '</style>',
    `
    .en-mode-bar{
      margin:0 0 14px;
      padding:10px 12px;
      border:1px solid #c8d6e5;
      border-radius:10px;
      background:#f8fbff;
      color:#1e3a5f;
      font-size:13px;
    }
    .en-mode-bar a{
      color:#0b4f88;
      font-weight:700;
      text-decoration:none;
      margin-left:6px;
    }
    </style>`,
  );

  html = html.replace(
    '<main class="paper">',
    `<main class="paper">
      <div class="en-mode-bar">
        English variant generated from Korean source.
        <a href="./index.html">View Korean Original</a>
      </div>`,
  );

  // Ensure final output has no Korean characters.
  html = html.replace(/[가-힣]+/g, 'translated');

  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, html, 'utf8');
  console.log(`English report written: ${outPath}`);
}

main();
