#!/usr/bin/env node
/**
 * render_professional_report.mjs
 * v2: replaced custom parser with `marked` to fix V8 memory crash
 */
import fs from 'node:fs';
import path from 'node:path';
import { marked } from 'marked';

function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function localizeHeadingText(text) {
  let out = String(text || '').trim();
  const r = [
    [/16-Country Full Coverage Dashboard/gi, '핵심 법인 종합 커버리지 대시보드'],
    [/LG Electronics Global D2C Weekly Market Intelligence Report/gi, 'LG전자 글로벌 D2C 주간 시장 인텔리전스 리포트'],
    [/16-Country Full Coverage/gi, '핵심 법인 풀 커버리지'],
    [/Executive Summary/gi, '경영진 요약'],
    [/Critical Alerts/gi, '핵심 경보'],
    [/Key Insight/gi, '핵심 인사이트'],
    [/Action Required/gi, '실행 필요'],
    [/Key Findings/gi, '핵심 발견'],
    [/This Week'?s Numbers/gi, '이번 주 주요 지표'],
    [/Recommended Actions/gi, '권장 실행 과제'],
    [/Consumer Sentiment Monitoring/gi, '소비자 반응 모니터링'],
    [/Retail Channel Promotion Monitoring/gi, '유통 채널 프로모션 모니터링'],
    [/Competitive Price\s*&\s*Positioning/gi, '경쟁 가격 및 포지셔닝'],
    [/Chinese Brand Threat Tracking/gi, '중국 브랜드 위협 추적'],
    [/Chinese Brand Threat Report/gi, '중국 브랜드 위협 보고'],
    [/Brand-by-Brand Analysis/gi, '브랜드별 분석'],
    [/Chinese Brand Price War Map/gi, '중국 브랜드 가격 전쟁 맵'],
    [/Strategic Summary/gi, '전략 요약'],
    [/Week-over-Week Trend/gi, '전주 대비 추이'],
    [/16개국 Alert Map/gi, '핵심 법인 알림 맵'],
    [/Consumer Negative Alerts/gi, '소비자 부정 알림'],
    [/Competitor Aggressive Moves/gi, '경쟁사 공격 행보'],
    [/Chinese Brand Momentum Alerts/gi, '중국 브랜드 모멘텀 알림'],
    [/Appendix A:\s*Data Sources\s*&\s*Coverage/gi, '부록 A: 데이터 소스 및 커버리지'],
    [/Appendix B:\s*Methodology\s*&\s*Limitations/gi, '부록 B: 방법론 및 한계'],
    [/Appendix C:\s*Glossary/gi, '부록 C: 용어집'],
  ];
  r.forEach(([p,n]) => { out = out.replace(p,n); });
  out = out.replace(/16개국/g, '핵심 법인').replace(/16-country/gi, '핵심 법인');
  return out;
}

function resolveTocLevel(level, text) {
  const t = String(text||'').trim();
  if (level===2) { if (/^appendix\b/i.test(t)) return 2; if (/^\d+\.\d+/.test(t)) return 3; return 2; }
  if (level===3) { if (/^\d+\.\d+\.\d+/.test(t)) return 4; return 3; }
  return level;
}

function renderMarkdown(md, lang) {
  const toc = [];
  let hCount = 0;
  const renderer = new marked.Renderer();

  renderer.heading = function({ tokens, depth }) {
    const text = this.parser.parseInline(tokens);
    const plain = text.replace(/<[^>]+>/g, '');
    const loc = lang==='ko' ? localizeHeadingText(plain) : plain;
    hCount++;
    const id = `sec-${hCount}`;
    const isKI = depth===3 && /^(key insight|핵심 인사이트)$/i.test(plain.trim());
    const isAR = depth===3 && /^(action required|실행 필요)$/i.test(plain.trim());
    const cls = [depth===1?'report-title':depth===2?'section-title':'sub-title'];
    if (isKI) cls.push('key-insight-banner');
    if (isAR) cls.push('action-required-banner');
    const excl = depth===3 && /^(key insight|action required|핵심 인사이트|실행 필요)$/i.test(plain.trim());
    if (depth>=2 && depth<=3 && !excl) toc.push({level:resolveTocLevel(depth,loc),text:lang==='ko'?localizeHeadingText(loc):loc,id});
    const disp = lang==='ko' ? localizeHeadingText(text) : text;
    return `<h${depth} id="${id}" class="${cls.join(' ')}">${disp}</h${depth}>\n`;
  };

  renderer.table = function({ header, rows }) {
    const hc = header.map(c=>`<th>${this.parser.parseInline(c.tokens)}</th>`).join('');
    const br = rows.map(r=>`<tr>${r.map(c=>`<td>${this.parser.parseInline(c.tokens)}</td>`).join('')}</tr>`).join('\n');
    return `<div class="table-wrap"><table><thead><tr>${hc}</tr></thead><tbody>${br}</tbody></table></div>\n`;
  };

  renderer.hr = function() { return '<hr class="section-divider" />\n'; };

  const chartProcessed = md.replace(
    /<!--\s*CHART:(\w+)\s*-->\s*\n\s*```json:chart\n([\s\S]*?)```/g,
    (_, cid, js) => { try { const d=JSON.parse(js.trim()); return `<div class="chart-container"><canvas id="chart-${cid}" data-chart='${JSON.stringify(d).replace(/'/g,"&#39;")}'></canvas></div>`; } catch{return '';} }
  );

  marked.setOptions({ gfm:true, breaks:false, pedantic:false, renderer });
  const body = marked.parse(chartProcessed);
  return { body, toc };
}

function buildHtml({title,subtitle,period,body,toc,lang,isMonthly}) {
  const hl = lang==='en'?'en':'ko';
  const tt = lang==='en'?'Quick Navigation':'바로가기 메뉴';
  const pl = lang==='en'?'Report Period':'보고 기간';
  const th = toc.map(t=>`<li class="l${t.level}"><a href="#${t.id}">${escapeHtml(t.text)}</a></li>`).join('');
  return `<!doctype html>
<html lang="${hl}">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>${escapeHtml(title)}</title>
<style>
:root{--bg:#f6f8fb;--paper:#fff;--ink:#0f172a;--muted:#475569;--line:#dbe2ea;--brand:#005a9c;--alert:#b91c1c;--warn:#a16207;--ok:#166534;--shadow:0 10px 30px rgba(15,23,42,.08)}
*{box-sizing:border-box}html,body{margin:0;padding:0;background:var(--bg);color:var(--ink)}
body{font:15px/1.6 "Noto Sans KR","Pretendard",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.layout{display:grid;grid-template-columns:290px minmax(0,1fr);gap:22px;max-width:1440px;margin:0 auto;padding:24px}
.toc-panel{position:sticky;top:18px;align-self:start;background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:14px;box-shadow:var(--shadow);max-height:calc(100vh - 36px);overflow:auto}
.toc-title{margin:0 0 10px;padding:10px 11px;border-radius:10px;background:linear-gradient(95deg,#003a66 0%,#005a9c 58%,#0a7ac4 100%);color:#fff;font-size:13px;font-weight:800;letter-spacing:.2px}
.toc-panel ul{margin:0;padding:0;list-style:none;display:grid;gap:6px}
.toc-panel li{margin:0}
.toc-panel a{display:block;color:#0b4f88;text-decoration:none;border:1px solid transparent;border-radius:9px;background:#f8fbff;padding:7px 10px;font-size:13px;line-height:1.35;transition:background-color .12s,border-color .12s,transform .12s}
.toc-panel a:hover{background:#edf5ff;border-color:#d5e5f6;transform:translateX(1px)}
.toc-panel a:focus-visible{outline:3px solid rgba(10,122,196,.35);outline-offset:1px}
.toc-panel li.l3 a{margin-left:12px;background:#fcfdff;color:#28435f}
.toc-panel li.l4 a{margin-left:24px;background:#fff;color:#3f5871;font-size:12px}
.toc-panel a.is-active{background:#e5f1ff;border-color:#c9ddf3;color:#0b4f88;font-weight:800}
.paper{background:var(--paper);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);overflow:hidden}
.cover{background:linear-gradient(140deg,#003a66,#005a9c 55%,#0a7ac4);color:#fff;padding:34px 36px}
.cover h1{margin:0 0 8px;font-size:34px;line-height:1.2;font-weight:800}
.cover p{margin:6px 0;opacity:.95}
.cover .meta{margin-top:14px;font-size:14px;opacity:.92}
.content{padding:30px 34px 38px}
.report-title{margin-top:8px;font-size:30px;line-height:1.25}
.section-title{margin:30px 0 12px;font-size:22px;color:#fff;border-left:0;padding:12px 14px;border-radius:12px;background:linear-gradient(95deg,#003a66 0%,#005a9c 58%,#0a7ac4 100%);box-shadow:0 8px 18px rgba(15,23,42,.12);letter-spacing:.1px;line-height:1.35}
.sub-title{margin:20px 0 10px;font-size:17px;color:#0b3354;border:1px solid #cfe0f1;border-radius:10px;padding:9px 12px;background:linear-gradient(120deg,#f8fbff 0%,#eef5fd 100%);box-shadow:0 4px 10px rgba(15,23,42,.06);line-height:1.35}
.sub-title.key-insight-banner{border-color:#d1e4f7;background:linear-gradient(120deg,#eff7ff 0%,#e5f1ff 100%);color:#0b4f88;font-weight:800}
.sub-title.action-required-banner{border-color:#f1dfc4;background:linear-gradient(120deg,#fff8ea 0%,#ffefcf 100%);color:#8a4b00;font-weight:800}
p{margin:10px 0}
hr.section-divider{border:0;border-top:1px solid var(--line);margin:18px 0}
blockquote{margin:14px 0;padding:10px 14px;border-left:4px solid var(--brand);background:#eef6fc;color:#15324a}
a{color:var(--brand);text-decoration:none}a:hover{text-decoration:underline}
ul,ol{margin:8px 0 10px 22px}
.chart-container{max-width:800px;margin:18px auto 24px;padding:16px;background:var(--paper);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow)}
.chart-container canvas{width:100%!important;min-height:300px;height:400px!important}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px;margin:12px 0 18px}
table{width:100%;border-collapse:collapse;min-width:760px;background:#fff;font-size:14px}
th,td{border-bottom:1px solid #e7edf4;border-right:1px solid #eef3f8;padding:8px 10px;vertical-align:top;text-align:left}
th:last-child,td:last-child{border-right:0}
thead th{position:sticky;top:0;z-index:1;background:#f1f7fd;color:#15324a;font-weight:700}
code{background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:1px 5px;font-size:.92em}
.foot{border-top:1px solid var(--line);color:var(--muted);padding:14px 34px 24px;font-size:13px}
@media(max-width:1100px){.layout{grid-template-columns:1fr;padding:14px}.toc-panel{position:relative;top:0;max-height:none}.toc-title{margin-bottom:8px}.toc-panel li.l3 a,.toc-panel li.l4 a{margin-left:0}.cover h1{font-size:28px}.content{padding:20px 16px 28px}.foot{padding:14px 16px 22px}.section-title{font-size:20px}.sub-title{font-size:17px}}
@media print{body{background:#fff}.layout{display:block;max-width:none;padding:0}.toc-panel{display:none}.paper{border:none;box-shadow:none}.cover{border-radius:0}.content{padding:18mm 12mm 16mm}.foot{padding:8mm 12mm 0}.section-title{break-after:avoid}.section-title,.sub-title{background:#fff!important;color:#003a66!important;border:1px solid #cfd8e3!important;box-shadow:none!important}.table-wrap{break-inside:avoid}a{color:#003a66}}

.monthly{--brand:#9c1a1a}
.monthly .toc-title{background:linear-gradient(95deg,#4a0e0e 0%,#9c1a1a 58%,#c43a0a 100%)}
.monthly .toc-panel a{color:#881a0b;background:#fff8f6}
.monthly .toc-panel a:hover{background:#ffedea;border-color:#f6d5d0}
.monthly .toc-panel a:focus-visible{outline-color:rgba(196,58,10,.35)}
.monthly .toc-panel li.l3 a{background:#fffcfb;color:#5f2818}
.monthly .toc-panel li.l4 a{color:#71382a}
.monthly .toc-panel a.is-active{background:#ffe5e3;border-color:#f3c9c9;color:#881a0b}
.monthly .cover{background:linear-gradient(140deg,#4a0e0e,#9c1a1a 55%,#c43a0a)}
.monthly .section-title{background:linear-gradient(95deg,#4a0e0e 0%,#9c1a1a 58%,#c43a0a 100%);box-shadow:0 8px 18px rgba(74,14,14,.15)}
.monthly .sub-title{color:#3b1010;border-color:#f1cfcf;background:linear-gradient(120deg,#fff8f8 0%,#fdeeed 100%)}
.monthly .sub-title.key-insight-banner{border-color:#f1d1cf;background:linear-gradient(120deg,#fff0ef 0%,#ffe5e3 100%);color:#881a0b}
.monthly .sub-title.action-required-banner{border-color:#f1dfc4;background:linear-gradient(120deg,#fff8ea 0%,#ffefcf 100%);color:#8a4b00}
.monthly blockquote{border-left-color:#9c1a1a;background:#fceeed;color:#3b1515}
.monthly a{color:#9c1a1a}
.monthly thead th{background:#fdf1f1;color:#3b1515}
.monthly .foot{border-top-color:#f1cfcf}
@media print{.monthly .section-title,.monthly .sub-title{color:#4a0e0e!important}.monthly a{color:#4a0e0e}}
</style>
</head>
<body${isMonthly?' class="monthly"':''}>
<nav style="background:#0f3f67;padding:10px 20px;display:flex;gap:16px;align-items:center;font:14px sans-serif;position:sticky;top:0;z-index:1000"><a href="/d2c-intel/" style="color:#fbbf24;text-decoration:none;font-weight:800">🌐 Hub</a><a href="/d2c-intel/reports/html/latest/hub.html" style="color:#93c5fd;text-decoration:none">📋 Weekly</a><a href="/d2c-intel/monthly/latest/index.html" style="color:#fde68a;text-decoration:none">📊 Monthly</a><a href="/d2c-intel/monthly/latest/index_en.html" style="color:#d1d5db;text-decoration:none">Monthly EN</a></nav>
<div class="layout">
<aside class="toc-panel"><div class="toc-title">${tt}</div><ul>${th}</ul></aside>
<main class="paper">
<header class="cover"><h1>${escapeHtml(title)}</h1><p>${escapeHtml(subtitle)}</p><p class="meta">${pl}: ${escapeHtml(period)}</p></header>
<section class="content">${body}</section>
<footer class="foot">Generated for executive sharing · LG Global D2C Intelligence</footer>
</main>
</div>
<script>
(function(){var tl=Array.from(document.querySelectorAll('.toc-panel a[href^="#"]'));if(!tl.length)return;var m=new Map();tl.forEach(function(l){var id=(l.getAttribute('href')||'').slice(1);if(id)m.set(id,l)});function sa(id){tl.forEach(function(l){l.classList.remove('is-active')});var t=m.get(id);if(t)t.classList.add('is-active')}var hs=Array.from(m.keys()).map(function(id){return document.getElementById(id)}).filter(Boolean);if(!hs.length)return;sa(hs[0].id);var ob=new IntersectionObserver(function(es){var v=es.filter(function(e){return e.isIntersecting}).sort(function(a,b){return a.boundingClientRect.top-b.boundingClientRect.top});if(v.length)sa(v[0].target.id)},{root:null,rootMargin:'-22% 0px -64% 0px',threshold:[0,1]});hs.forEach(function(h){ob.observe(h)});tl.forEach(function(l){l.addEventListener('click',function(){var id=(l.getAttribute('href')||'').slice(1);if(id)sa(id)})})})();
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
(function(){document.querySelectorAll('canvas[data-chart]').forEach(function(c){try{var d=JSON.parse(c.getAttribute('data-chart'));if(!d||!d.type)return;var ctx=c.getContext('2d');var ds=(d.datasets||[]).map(function(s){var b={label:s.label||'',data:s.data||[]};if(d.type==='doughnut'||d.type==='polarArea'){b.backgroundColor=(s.data||[]).map(function(_,i){return['#003a66','#0a7ac4','#2196F3','#4CAF50','#FF9800','#e63946','#9c27b0','#607d8b'][i%8]})}else{b.borderColor=s.color||'#003a66';b.backgroundColor=(s.color||'#003a66')+'33';b.tension=0.3;b.fill=d.type==='line'}return b});new Chart(ctx,{type:d.type,data:{labels:d.labels||[],datasets:ds},options:{responsive:true,maintainAspectRatio:true,plugins:{title:{display:true,text:d.title||'',font:{size:16}},legend:{position:'bottom'}},scales:(d.type==='doughnut'||d.type==='polarArea')?{}:{y:{beginAtZero:true}}}})}catch(e){}})})();
</script>
</body>
</html>`;
}

function main() {
  const [,,inputFile,outputHtml,langArg] = process.argv;
  if (!inputFile||!outputHtml) { console.error('Usage: node render_professional_report.mjs <input.md> <output.html> [ko|en]'); process.exit(1); }
  const lang = langArg==='en'?'en':'ko';
  const absIn = path.resolve(inputFile), absOut = path.resolve(outputHtml);
  const md = fs.readFileSync(absIn,'utf8');
  const {body,toc} = renderMarkdown(md,lang);
  const isM = /monthly|월간/i.test(md.slice(0,500));
  const title = isM?(lang==='en'?'LG Electronics Global D2C Monthly Deep Dive Intelligence Report':'LG전자 글로벌 D2C 월간 시장 심화 분석 리포트'):(lang==='en'?'LG Electronics Global D2C Weekly Market Intelligence Report':'LG전자 글로벌 D2C 주간 시장 인텔리전스 리포트');
  const subtitle = isM?(lang==='en'?'Consumer Sentiment · Retail Promotion · Price Intelligence · Chinese Brand Tracking — Monthly Trend Analysis':'소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향 — 월간 추세 분석'):(lang==='en'?'Consumer Sentiment · Retail Channel Promotion · Price Intelligence · Chinese Brand Tracking':'소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향');
  const pm = md.match(/(?:Report Period|보고 기간):\s*([^\n]+)/);
  const period = pm?pm[1].trim():'N/A';
  const html = buildHtml({title,subtitle,period,body,toc,lang,isMonthly:isM});
  fs.mkdirSync(path.dirname(absOut),{recursive:true});
  fs.writeFileSync(absOut,html,'utf8');
  console.log(`[render] ✅ ${absOut} (${(html.length/1024).toFixed(1)}KB)`);
}

main();
