#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function usage() {
  console.error('Usage: node render_reports_hub.mjs <manifest_json> <output_html>');
  process.exit(1);
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeRegex(str) {
  return String(str).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function stripHtml(str) {
  return String(str)
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

function extractEnglishInsightsFromReport(reportPath, maxCount = 3) {
  try {
    if (!fs.existsSync(reportPath)) return [];
    const html = fs.readFileSync(reportPath, 'utf8');
    const match =
      html.match(/<h3[^>]*class="[^"]*key-insight-banner[^"]*"[^>]*>[\s\S]*?<\/h3>\s*<ul>([\s\S]*?)<\/ul>/i) ||
      html.match(/<h3[^>]*>\s*Key Insights?\s*<\/h3>\s*<ul>([\s\S]*?)<\/ul>/i);
    if (!match) return [];
    const liMatches = Array.from(match[1].matchAll(/<li[^>]*>([\s\S]*?)<\/li>/gi));
    return liMatches
      .map((m) => stripHtml(m[1]))
      .filter((text) => {
        if (!text) return false;
        if (/translatedtranslated/i.test(text)) return false;
        const translatedHits = (text.match(/\btranslated\b/gi) || []).length;
        return translatedHits < 3;
      })
      .slice(0, maxCount);
  } catch {
    return [];
  }
}

function numericOrNull(v) {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function plusDelta(a, b) {
  const av = numericOrNull(a);
  const bv = numericOrNull(b);
  if (av === null || bv === null) return null;
  return av - bv;
}

function deltaLabel(delta) {
  if (delta === null) return '-';
  if (delta > 0) return `+${delta}`;
  return `${delta}`;
}

function deltaClass(delta) {
  if (delta === null || delta === 0) return 'flat';
  return delta > 0 ? 'up' : 'down';
}

function linkFromHub(link, fallback = '#') {
  if (!link) return fallback;
  const raw = String(link).trim();
  const clean = raw.split(/[?#]/)[0];
  const fileName = clean.split('/').pop() || '';
  const lower = clean.toLowerCase();

  if (
    lower.startsWith('file://') ||
    lower.startsWith('/users/') ||
    /^[a-z]:\\/.test(lower)
  ) {
    if (fileName.toLowerCase().endsWith('.pdf')) return `../pdf/${fileName}`;
    if (fileName.toLowerCase().endsWith('.md')) return `../md/${fileName}`;
    if (fileName.toLowerCase().endsWith('.html')) return `../${fileName}`;
  }

  if (lower.includes('/pdf/') && fileName.toLowerCase().endsWith('.pdf')) {
    return `../pdf/${fileName}`;
  }
  if (lower.includes('/md/') && fileName.toLowerCase().endsWith('.md')) {
    return `../md/${fileName}`;
  }

  if (raw.startsWith('http://') || raw.startsWith('https://') || raw.startsWith('/')) return raw;
  if (raw.startsWith('./')) return `../${raw.slice(2)}`;
  if (raw.startsWith('../')) return `../${raw}`;
  return `../${raw}`;
}

function insightPreview(w, count = 2) {
  const items = Array.isArray(w.executive_key_insights) ? w.executive_key_insights.slice(0, count) : [];
  if (!items.length) {
    return '<li>Open report to view insights</li>';
  }
  return items.map((x) => `<li>${escapeHtml(x)}</li>`).join('');
}

function weekCardHtml(w, idx) {
  const m = w.metrics || {};
  const badge = idx === 0 ? 'Latest' : `W-${idx}`;
  const periodText = `${escapeHtml(w.report_period?.start || '-')} ~ ${escapeHtml(w.report_period?.end || '-')}`;
  const links = w.links || {};
  const htmlLink = linkFromHub(links.html, `../${w.week}/index.html`);
  const pdfLink = linkFromHub(links.pdf, '#');
  const mdLink = linkFromHub(links.md, '#');
  const token = [w.week, w.report_period?.start, w.report_period?.end, ...(w.executive_key_insights || [])].join(' ').toLowerCase();

  return `
    <article class="week-card" data-week="${escapeHtml(w.week)}" data-month="${escapeHtml((w.week || '').slice(0, 7))}" data-search="${escapeHtml(token)}">
      <div class="head">
        <div class="week">${escapeHtml(w.week)}</div>
        <span class="badge">${escapeHtml(badge)}</span>
      </div>
      <div class="period">기간: ${periodText}</div>
      <div class="metrics">
        <div>Coverage <strong>${escapeHtml(m.covered_countries ?? '-')}</strong></div>
        <div>Critical <strong>${escapeHtml(m.critical_country_count ?? '-')}</strong></div>
        <div>Comp Promo <strong>${escapeHtml(m.competitor_promotion_signals ?? '-')}</strong></div>
        <div>China Threat <strong>${escapeHtml(m.chinese_threat_signals ?? '-')}</strong></div>
      </div>
      <div class="insight-mini">
        <div class="mini-title">Key Insight</div>
        <ul>${insightPreview(w, 2)}</ul>
      </div>
      <div class="links">
        <a class="btn primary" href="${escapeHtml(htmlLink)}">Report</a>
        <a class="btn" href="${escapeHtml(pdfLink)}">PDF</a>
      </div>
    </article>
  `;
}

function latestHeroHtml(latest) {
  if (!latest) {
    return `
      <article class="panel hero-card">
        <div class="hero-meta">Latest Issue</div>
        <h2>데이터 없음</h2>
      </article>
    `;
  }

  const links = latest.links || {};
  const htmlLink = linkFromHub(links.html, `../${latest.week}/index.html`);
  const pdfLink = linkFromHub(links.pdf, '#');
  const periodText = `${escapeHtml(latest.report_period?.start || '-')} ~ ${escapeHtml(latest.report_period?.end || '-')}`;

  return `
    <article class="panel hero-card" id="latestIssue">
      <div class="hero-meta">Latest Issue</div>
      <h2>${escapeHtml(latest.week)}</h2>
      <p class="hero-period">Report Period: ${periodText}</p>
      <p class="hero-desc">이번 주 리포트로 바로 이동해 핵심 시그널을 확인합니다.</p>
      <div class="insight-mini hero-insight">
        <div class="mini-title">Key Insight Preview</div>
        <ul>${insightPreview(latest, 3)}</ul>
      </div>
      <div class="hero-actions">
        <a class="btn primary" href="${escapeHtml(htmlLink)}">Report</a>
        <a class="btn" href="${escapeHtml(pdfLink)}">PDF</a>
      </div>
    </article>
  `;
}

function trendSummaryHtml(latest, prev) {
  if (!latest || !prev) {
    return '<div class="trend-msg">전주 데이터가 누적되면 자동으로 비교 요약이 표시됩니다.</div>';
  }
  const metrics = [
    ['Critical 국가 수', plusDelta(latest.metrics?.critical_country_count, prev.metrics?.critical_country_count)],
    ['LG 프로모션 신호', plusDelta(latest.metrics?.lg_promotion_signals, prev.metrics?.lg_promotion_signals)],
    ['경쟁사 프로모션 신호', plusDelta(latest.metrics?.competitor_promotion_signals, prev.metrics?.competitor_promotion_signals)],
    ['중국 브랜드 위협 신호', plusDelta(latest.metrics?.chinese_threat_signals, prev.metrics?.chinese_threat_signals)],
  ];
  return `
    <div class="trend-grid">
      ${metrics
        .map(
          (row) => `
        <div class="trend-card">
          <div class="label">${escapeHtml(row[0])}</div>
          <div class="value delta ${escapeHtml(deltaClass(row[1]))}">${escapeHtml(deltaLabel(row[1]))}</div>
        </div>
      `,
        )
        .join('')}
    </div>
  `;
}

function buildEnglishHubHtml(koHtml, weeks, outputHtml) {
  const replacements = [
    ['<html lang="ko">', '<html lang="en">'],
    ['주차별 보고서 접근, 비교, 핵심 지표 확인을 위한 메인 허브', 'Main hub for weekly report access, comparison, and key metrics'],
    ['<a class="lang-link active" href="./hub.html">🇰🇷 한국어</a>', '<a class="lang-link" href="./hub.html">🇰🇷 한국어</a>'],
    ['<a class="lang-link" href="./hub_en.html">🇺🇸 English</a>', '<a class="lang-link active" href="./hub_en.html">🇺🇸 English</a>'],
    ['최신 보고서', 'Latest Report'],
    ['최신 PDF', 'Latest PDF'],
    ['이번 주 리포트로 바로 이동해 핵심 시그널을 확인합니다.', "Jump to this week's report and check the key market signals."],
    ['최신 주차 전주 대비', 'Latest vs Previous Week'],
    ['Critical 국가 수', 'Critical Countries'],
    ['LG 프로모션 신호', 'LG Promotion Signals'],
    ['경쟁사 프로모션 신호', 'Competitor Promotion Signals'],
    ['중국 브랜드 위협 신호', 'China Brand Threat Signals'],
    ['전주 데이터가 누적되면 자동으로 비교 요약이 표시됩니다.', 'The comparison summary appears automatically once previous-week data is available.'],
    ['누적 주차:', 'Total reports:'],
    ['날짜 범위:', 'Date range:'],
    ['평균 간격:', 'Avg cadence:'],
    ['기간:', 'Period:'],
    ['검색 결과가 없습니다.', 'No results found.'],
    ['커버 국가 수', 'Covered Countries'],
    ['경쟁사 공격 프로모션', 'Competitor Aggressive Promotions'],
    ['링크가 복사되었습니다.', 'Link copied.'],
    ['복사할 링크입니다:', 'Copy this link:'],
    ['주차별 추이 그래프', 'Weekly Trend Chart'],
    ['선택 주차 A/B 그래프', 'Selected Week A/B Chart'],
    ['주간 아카이브 탐색기', 'WEEKLY ARCHIVE EXPLORER'],
    ['전주 대비 비교', 'WEEK-OVER-WEEK COMPARE'],
    ['Consumer Negative 국가 수', 'Consumer Negative Countries'],
    ['📬 D2C Weekly Intelligence를 이메일로 받아보세요', '📬 Subscribe to D2C Weekly Intelligence via email'],
    ['매주 월요일, 최신 글로벌 D2C 시장 인사이트를 전달합니다', 'Get the latest global D2C market insights delivered every Monday'],
    ['✉️ 구독 신청', '✉️ Subscribe'],
    ['💡 Key Insight', '💡 Key Insight'],
  ];

  let out = koHtml;
  for (const [from, to] of replacements) {
    out = out.split(from).join(to);
  }
  out = out.replace(/(\.\.\/\d{4}-\d{2}-\d{2}\/)index\.html/g, '$1index_en.html');
  out = out.replace(/(\.\/\d{4}-\d{2}-\d{2}\/)index\.html/g, '$1index_en.html');

  const outputDir = path.dirname(path.resolve(outputHtml));
  const englishInsightsByWeek = new Map();
  for (const w of weeks || []) {
    const htmlHref = linkFromHub(w?.links?.html, `../${w?.week || ''}/index.html`);
    const resolvedHtml = path.resolve(outputDir, htmlHref);
    const enReportPath = resolvedHtml.replace(/index\.html$/i, 'index_en.html');
    const insights = extractEnglishInsightsFromReport(enReportPath, 3);
    if (insights.length) {
      englishInsightsByWeek.set(w.week, insights);
    }
  }

  const latestWeek = weeks?.[0]?.week;
  const latestInsights = (englishInsightsByWeek.get(latestWeek) || []).filter((text) => !/\btranslated\b/i.test(text));
  const latestInsightLis = latestInsights.length
    ? latestInsights.map((x) => `<li>${escapeHtml(x)}</li>`).join('')
    : '<li>Open report for full insight details in English.</li>';

  out = out.replace(
    /(<div class="mini-title">Key Insight Preview<\/div>\s*<ul>)[\s\S]*?(<\/ul>)/,
    (_, p1, p2) => `${p1}${latestInsightLis}${p2}`,
  );

  for (const w of weeks || []) {
    const insights = (englishInsightsByWeek.get(w.week) || []).filter((text) => !/\btranslated\b/i.test(text));
    const insightLis = insights.length
      ? insights.slice(0, 2).map((x) => `<li>${escapeHtml(x)}</li>`).join('')
      : '<li>Open report for full insight details in English.</li>';
    const cardPattern = new RegExp(
      `(<article class="week-card"[^>]*data-week="${escapeRegex(w.week)}"[\\s\\S]*?<div class="mini-title">Key Insight<\\/div>\\s*<ul>)[\\s\\S]*?(<\\/ul>)`,
      'i',
    );
    out = out.replace(cardPattern, (_, p1, p2) => `${p1}${insightLis}${p2}`);
  }
  return out;
}

function main() {
  const [, , manifestPath, outputHtml] = process.argv;
  if (!manifestPath || !outputHtml) usage();

  const manifest = JSON.parse(fs.readFileSync(path.resolve(manifestPath), 'utf8'));
  const weeks = (manifest.weeks || []).slice();
  const latest = weeks[0] || null;
  const previous = weeks[1] || null;
  const latestMetrics = latest?.metrics || {};

  const weekCards = weeks.map((w, i) => weekCardHtml(w, i)).join('');
  const latestHero = latestHeroHtml(latest);
  const trendSummary = trendSummaryHtml(latest, previous);

  const options = weeks
    .map((w, i) => `<option value="${escapeHtml(w.week)}"${i === 0 ? ' selected' : ''}>${escapeHtml(w.week)}</option>`)
    .join('');
  const secondOptions = weeks
    .map((w, i) => `<option value="${escapeHtml(w.week)}"${i === 1 ? ' selected' : ''}>${escapeHtml(w.week)}</option>`)
    .join('');

  const payload = JSON.stringify(manifest).replace(/</g, '\\u003c');

  const html = `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>LG D2C Weekly Hub</title>
  <!-- Updated: hub UX-only redesign while preserving archive/compare core functions. Weekly report files are untouched. -->
  <style>
    :root{
      --bg:#f4f7fb;
      --surface:#ffffff;
      --ink:#0f172a;
      --muted:#475569;
      --line:#d7e2ef;
      --brand:#005a9c;
      --brand-2:#0a7ac4;
      --banner:#0f3f67;
      --up:#166534;
      --down:#b91c1c;
      --flat:#334155;
      --shadow:0 10px 28px rgba(15,23,42,.08);
      --rad:14px;
    }
    *{box-sizing:border-box}
    html,body{margin:0}
    body{
      background:
        radial-gradient(1200px 500px at 95% -20%,#d9ebfb 0%,transparent 60%),
        var(--bg);
      color:var(--ink);
      font:15px/1.55 "Noto Sans KR","Pretendard",-apple-system,BlinkMacSystemFont,sans-serif;
    }
    .wrap{max-width:1480px;margin:0 auto;padding:20px}
    .topbar{
      background:linear-gradient(145deg,#003a66,#005a9c 55%,#0a7ac4);
      color:#fff;
      border-radius:18px;
      box-shadow:var(--shadow);
      padding:22px 24px;
      margin-bottom:14px;
    }
    .topbar h1{margin:0;font-size:28px;letter-spacing:.2px}
    .topbar p{margin:8px 0 0;opacity:.95}
    .meta{margin-top:10px;font-size:13px;opacity:.92;display:flex;gap:14px;flex-wrap:wrap}
    .lang-switch{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}
    .lang-link{
      display:inline-flex;
      align-items:center;
      gap:6px;
      padding:6px 10px;
      border-radius:999px;
      border:1px solid rgba(255,255,255,.5);
      color:#eaf3ff;
      text-decoration:none;
      font-weight:700;
      font-size:13px;
      background:rgba(255,255,255,.08);
    }
    .lang-link.active{
      background:#ffffff;
      color:#0b4f88;
      border-color:#ffffff;
    }
    .newsletter-bar{
      position:sticky;
      top:8px;
      z-index:20;
      margin-bottom:14px;
      padding:14px 20px;
      background:linear-gradient(135deg,#003a66 0%,#005a9c 50%,#0a7ac4 100%);
      border-radius:14px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      box-shadow:0 6px 20px rgba(0,58,102,.25);
      color:#fff;
      flex-wrap:wrap;
    }
    .newsletter-bar .nl-text{font-size:15px;font-weight:700;letter-spacing:.2px}
    .newsletter-bar .nl-sub{font-size:12px;opacity:.85;margin-top:2px}
    .newsletter-bar .nl-btn{
      display:inline-flex;align-items:center;gap:6px;
      padding:9px 18px;border-radius:999px;
      background:#fff;color:#005a9c;
      font-weight:800;font-size:14px;
      text-decoration:none;border:none;cursor:pointer;
      box-shadow:0 2px 8px rgba(0,0,0,.12);
      transition:transform .15s;
    }
    .newsletter-bar .nl-btn:hover{transform:scale(1.04)}

    .archive-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-left:auto}
    .archive-controls select{border:1px solid #bcd0e3;border-radius:9px;padding:6px 10px;font:inherit;background:#fff}

    .archive-header{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:15px 16px 8px}
    .archive-header h2{margin:0;font-size:20px;letter-spacing:.1px;flex:1}

    .timeline-list{position:relative;padding-left:28px}
    .timeline-list::before{content:'';position:absolute;left:11px;top:0;bottom:0;width:2px;background:linear-gradient(180deg,#0a7ac4,#dbe6f2);border-radius:2px}
    .timeline-card{position:relative;margin-bottom:12px}
    .timeline-card::before{content:'';position:absolute;left:-21px;top:16px;width:10px;height:10px;border-radius:50%;background:#0a7ac4;border:2px solid #fff;box-shadow:0 0 0 2px #0a7ac4;z-index:1}
    .timeline-card.latest::before{background:#b91c1c;box-shadow:0 0 0 2px #b91c1c}
    .timeline-card .week-card{border-left:3px solid #0a7ac4}
    .timeline-card.latest .week-card{border-left:3px solid #b91c1c}

    .metric-badges{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
    .metric-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:999px;font-size:12px;font-weight:700}
    .metric-badge.critical{background:#fef2f2;color:#b91c1c;border:1px solid #fecaca}
    .metric-badge.lg{background:#eff6ff;color:#0a7ac4;border:1px solid #bfdbfe}
    .metric-badge.comp{background:#fff7ed;color:#b45309;border:1px solid #fed7aa}
    .metric-badge.china{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0}
    .metric-badge .delta-sm{font-size:11px;opacity:.8}

    .insight-bubble{margin-top:8px;position:relative;background:#f0f7ff;border:1px solid #bfdbfe;border-radius:12px;padding:10px 12px}
    .insight-bubble::before{content:'';position:absolute;left:16px;top:-6px;width:12px;height:12px;background:#f0f7ff;border-left:1px solid #bfdbfe;border-top:1px solid #bfdbfe;transform:rotate(45deg)}
    .insight-bubble .mini-title{font-size:12px;font-weight:800;color:#1f4f79;margin-bottom:4px}
    .insight-bubble ul{margin:0;padding-left:18px;color:#334155;font-size:13px}
    .insight-bubble li{margin:2px 0}

    .panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--rad);box-shadow:var(--shadow)}
    .panel h2{margin:0;padding:15px 16px 8px;font-size:20px;letter-spacing:.1px}
    .panel .body{padding:0 16px 16px}

    .hero-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:14px;margin-bottom:14px}
    .hero-card{padding:14px 16px}
    .hero-meta{display:inline-block;border:1px solid #b8d0e8;background:#eff6ff;color:#1f4f79;padding:3px 9px;border-radius:999px;font-size:12px;font-weight:700}
    .hero-card h2{margin:8px 0 0;padding:0;font-size:31px}
    .hero-period{margin:8px 0 4px;color:#334155;font-weight:600}
    .hero-desc{margin:0 0 10px;color:#475569}
    .hero-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
    .hero-insight{margin-top:10px}

    .banner{
      margin:18px 0 10px;
      border-radius:12px;
      padding:10px 14px;
      color:#fff;
      background:linear-gradient(90deg,#0c3a61,#145687 45%,#0c3a61);
      border:1px solid #0a3255;
      box-shadow:0 6px 18px rgba(12,58,97,.28);
      font-weight:800;
      letter-spacing:.6px;
      text-transform:uppercase;
    }

    .archive-summary{display:flex;justify-content:space-between;gap:8px;align-items:center;padding:9px 10px;border:1px solid #dbe5f1;border-radius:10px;background:#f8fbff;font-size:12px;color:#334155;margin:0 0 10px}
    .archive-grid{display:grid;gap:10px}
    details.month-group{border:1px solid #dbe5f1;border-radius:12px;background:#f8fbff;padding:8px}
    details.month-group summary{cursor:pointer;font-weight:800;color:#12466f;list-style:none}
    details.month-group summary::-webkit-details-marker{display:none}
    .month-meta{font-size:12px;color:#64748b;font-weight:600;margin-left:8px}

    .week-list{display:grid;gap:10px}
    .week-card{border:1px solid #d6e4f0;background:#f8fbff;border-radius:12px;padding:12px}
    .week-card .head{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:6px}
    .week-card .week{font-weight:800;color:#0b4f88}
    .badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;background:#e2ecf7;color:#23415f}
    .week-card .period{font-size:13px;color:#475569}
    .week-card .metrics{font-size:13px;color:#334155;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px 8px;margin-top:8px}

    .insight-mini{margin-top:8px;border:1px solid #dbe6f2;background:#fff;border-radius:10px;padding:8px}
    .mini-title{font-size:12px;font-weight:800;color:#1f4f79;margin-bottom:4px}
    .insight-mini ul{margin:0;padding-left:18px;color:#334155;font-size:13px}
    .insight-mini li{margin:2px 0}

    .links{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}

    .btn{
      border:1px solid #c4d6ea;
      background:#fff;
      color:#134e7a;
      border-radius:9px;
      padding:7px 10px;
      font-size:13px;
      font-weight:700;
      text-decoration:none;
      cursor:pointer;
      appearance:none;
      line-height:1;
    }
    .btn.primary{background:linear-gradient(180deg,#0e7bc7,#0467ae);border-color:#075f9c;color:#fff}
    .btn:hover{filter:brightness(.98)}
    .btn:focus-visible,
    a:focus-visible,
    input:focus-visible,
    select:focus-visible,
    summary:focus-visible{
      outline:2px solid #1d70b7;
      outline-offset:2px;
    }

    .kpi-row{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin-bottom:12px}
    .kpi{border:1px solid #dde7f1;background:#fff;border-radius:12px;padding:10px}
    .kpi .label{font-size:12px;color:#64748b}
    .kpi .value{margin-top:4px;font-size:22px;font-weight:800}

    .compare-toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:10px}
    .compare-toolbar label{display:flex;align-items:center;gap:6px;font-weight:700;color:#334155}

    table{width:100%;border-collapse:collapse;border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:14px}
    th,td{padding:8px 10px;border-bottom:1px solid #e7edf4;border-right:1px solid #edf2f7;text-align:left}
    th:last-child,td:last-child{border-right:0}
    thead th{background:#f1f7fd}
    .delta.up{color:var(--up);font-weight:700}
    .delta.down{color:var(--down);font-weight:700}
    .delta.flat{color:var(--flat);font-weight:700}

    .chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
    .chart-card{border:1px solid #dbe6f2;border-radius:10px;padding:10px;background:#fafcff}
    .chart-card h3{margin:0 0 8px;font-size:14px;color:#0b4f88}
    .legend{display:flex;flex-wrap:wrap;gap:8px 12px;font-size:12px;margin:0 0 8px;color:#334155}
    .legend-item{display:flex;align-items:center;gap:6px}
    .sw{width:10px;height:10px;border-radius:999px;display:inline-block}
    .sw.critical{background:#b91c1c}.sw.lg{background:#0a7ac4}.sw.comp{background:#b45309}.sw.china{background:#166534}
    .sw.a{background:#0a7ac4}.sw.b{background:#334155}
    svg.chart{width:100%;height:260px;border:1px solid #e5edf5;border-radius:8px;background:#fff}

    .trend-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
    .trend-card{border:1px solid #dbe6f2;border-radius:10px;padding:10px;background:#fafcff}
    .trend-card .label{font-size:12px;color:#64748b}
    .trend-card .value{margin-top:2px;font-size:20px;font-weight:800}
    .trend-msg{border:1px dashed #cfddea;border-radius:10px;padding:14px;background:#f8fbff;color:#334155}

    @media (max-width:1200px){
      .hero-grid{grid-template-columns:1fr}
      .trend-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
      .kpi-row{grid-template-columns:repeat(2,minmax(0,1fr))}
      .chart-grid{grid-template-columns:1fr}
    }
    @media (max-width:768px){
      .wrap{padding:14px}
      .topbar h1{font-size:22px}
      .hero-card h2{font-size:26px}
      .week-card .metrics{grid-template-columns:1fr}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header class="topbar">
      <h1>LG Global D2C Weekly Intelligence Hub</h1>
      <p>주차별 보고서 접근, 비교, 핵심 지표 확인을 위한 메인 허브</p>
      <div class="meta">
        <span>Latest Week: ${escapeHtml(latest?.week ?? '-')}</span>
        <span>Total Weeks: ${escapeHtml(manifest.total_weeks ?? 0)}</span>
        <span>Last Updated: ${escapeHtml(new Date().toLocaleString('ko-KR'))}</span>
      </div>
      <nav class="lang-switch" aria-label="Language switch">
        <a class="lang-link active" href="./hub.html">🇰🇷 한국어</a>
        <a class="lang-link" href="./hub_en.html">🇺🇸 English</a>
      </nav>
    </header>

    <div class="newsletter-bar" aria-label="Newsletter subscription">
      <div>
        <div class="nl-text">📬 D2C Weekly Intelligence를 이메일로 받아보세요</div>
        <div class="nl-sub">매주 월요일, 최신 글로벌 D2C 시장 인사이트를 전달합니다</div>
      </div>
      <a class="nl-btn" href="https://docs.google.com/forms/d/e/1FAIpQLSd8etnrJSjXFNMWFg0-TQjqur-JL0TK4anujlCyuJFcsWrkcQ/viewform" target="_blank" rel="noopener">✉️ 구독 신청</a>
    </div>

    <section class="hero-grid">
      ${latestHero}
      <article class="panel">
        <h2>최신 주차 전주 대비</h2>
        <div class="body">${trendSummary}</div>
      </article>
    </section>

    <div class="banner">주간 아카이브 탐색기</div>
    <section class="panel">
      <div class="archive-header">
        <h2>Weekly Archive</h2>
        <div class="archive-controls">
          <select id="archiveSort" aria-label="Sort archive">
            <option value="desc" selected>Newest</option>
            <option value="asc">Oldest</option>
          </select>
          <select id="archiveGroup" aria-label="Group archive">
            <option value="month" selected>Group: Month</option>
            <option value="flat">Group: Flat</option>
          </select>
        </div>
      </div>
      <div class="body">
        <div class="archive-summary" id="archiveStats">
          <span>누적 주차: <strong>${escapeHtml(manifest.total_weeks ?? weeks.length)}</strong></span>
          <span>날짜 범위: -</span>
          <span>평균 간격: -</span>
        </div>
        <div class="archive-grid">
          <div class="week-list timeline-list" id="weekList">${weekCards || '<div class="week-card">No data</div>'}</div>
        </div>
      </div>
    </section>

    <div class="banner">전주 대비 비교</div>
    <section class="panel">
      <h2>Week-over-Week Compare</h2>
      <div class="body">
        <div class="kpi-row" id="kpiRow">
          <div class="kpi"><div class="label">Covered Countries</div><div class="value">${escapeHtml(latestMetrics.covered_countries ?? '-')}</div></div>
          <div class="kpi"><div class="label">Critical Countries</div><div class="value">${escapeHtml(latestMetrics.critical_country_count ?? '-')}</div></div>
          <div class="kpi"><div class="label">LG Promotion Signals</div><div class="value">${escapeHtml(latestMetrics.lg_promotion_signals ?? '-')}</div></div>
          <div class="kpi"><div class="label">Competitor Promotion Signals</div><div class="value">${escapeHtml(latestMetrics.competitor_promotion_signals ?? '-')}</div></div>
          <div class="kpi"><div class="label">China Threat Signals</div><div class="value">${escapeHtml(latestMetrics.chinese_threat_signals ?? '-')}</div></div>
        </div>

        <div class="compare-toolbar">
          <label for="weekA">From <select id="weekA">${options}</select></label>
          <label for="weekB">To <select id="weekB">${secondOptions || options}</select></label>
        </div>

        <table>
          <thead><tr><th>Metric</th><th>A</th><th>B</th><th>Delta (A-B)</th></tr></thead>
          <tbody id="compareBody"></tbody>
        </table>

        <div class="chart-grid">
          <div class="chart-card">
            <h3>주차별 추이 그래프</h3>
            <div class="legend" id="trendLegend"></div>
            <svg class="chart" id="trendSvg" viewBox="0 0 700 260" preserveAspectRatio="none"></svg>
          </div>
          <div class="chart-card">
            <h3>선택 주차 A/B 그래프</h3>
            <div class="legend" id="compareLegend"></div>
            <svg class="chart" id="compareSvg" viewBox="0 0 700 260" preserveAspectRatio="none"></svg>
          </div>
        </div>

      </div>
    </section>
  </div>

  <script id="manifest-data" type="application/json">${payload}</script>
  <script>
    (function(){
      var manifest = JSON.parse(document.getElementById('manifest-data').textContent || '{"weeks":[]}');
      var weeks = (manifest.weeks || []).slice();
      var weekList = document.getElementById('weekList');
      var archiveSort = document.getElementById('archiveSort');
      var archiveGroup = document.getElementById('archiveGroup');
      var isEnglishPage = (document.documentElement.lang || '').toLowerCase() === 'en';

      function parseWeekDate(week){
        if (!week || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(week)) return null;
        var d = new Date(week + 'T00:00:00');
        return Number.isNaN(d.getTime()) ? null : d;
      }

      weeks.sort(function(a,b){
        var da = parseWeekDate(a.week);
        var db = parseWeekDate(b.week);
        if (!da && !db) return 0;
        if (!da) return 1;
        if (!db) return -1;
        return db.getTime() - da.getTime();
      });

      var metricsConfig = [
        ['covered_countries', '커버 국가 수'],
        ['critical_country_count', 'Critical 국가 수'],
        ['lg_promotion_signals', 'LG 프로모션 신호'],
        ['competitor_promotion_signals', '경쟁사 공격 프로모션'],
        ['chinese_threat_signals', '중국 브랜드 위협 신호'],
        ['consumer_negative_countries', 'Consumer Negative 국가 수']
      ];

      var chartSeries = [
        { key:'critical_country_count', label:'Critical', color:'#b91c1c' },
        { key:'lg_promotion_signals', label:'LG Promo', color:'#0a7ac4' },
        { key:'competitor_promotion_signals', label:'Comp Promo', color:'#b45309' },
        { key:'chinese_threat_signals', label:'China Threat', color:'#166534' }
      ];

      function getWeek(week){
        return weeks.find(function(w){ return w.week === week; });
      }

      function metricValue(week, key){
        var v = week && week.metrics ? week.metrics[key] : null;
        return typeof v === 'number' && Number.isFinite(v) ? v : null;
      }

      function fmtDelta(d){
        if (d === null || Number.isNaN(d)) return '-';
        if (d > 0) return '+' + d;
        return String(d);
      }

      function deltaCls(d){
        if (d === null || Number.isNaN(d) || d === 0) return 'flat';
        return d > 0 ? 'up' : 'down';
      }

      function localizeInsightText(text){
        if (!isEnglishPage) return text;
        if (/[가-힣]/.test(text || '')) return 'Open report for full insight details in English.';
        return text;
      }

      function resolveLinkFromHub(link, fallback){
        if (!link) return fallback || '#';
        var raw = String(link).trim();
        var clean = raw.split(/[?#]/)[0];
        var fileName = clean.split('/').pop() || '';
        var lower = clean.toLowerCase();

        if (isEnglishPage && /\\/\\d{4}-\\d{2}-\\d{2}\\/index\\.html$/i.test(clean)) {
          return raw.replace(/index\\.html(\\?[^#]*)?(#.*)?$/i, 'index_en.html$1$2');
        }

        if (lower.indexOf('file://') === 0 || lower.indexOf('/users/') === 0 || /^[a-z]:\\\\/.test(lower)) {
          if (/\\.pdf$/i.test(fileName)) return '../pdf/' + fileName;
          if (/\\.md$/i.test(fileName)) return '../md/' + fileName;
          if (/\\.html$/i.test(fileName)) return '../' + fileName;
        }

        if (lower.indexOf('/pdf/') >= 0 && /\\.pdf$/i.test(fileName)) return '../pdf/' + fileName;
        if (lower.indexOf('/md/') >= 0 && /\\.md$/i.test(fileName)) return '../md/' + fileName;

        if (raw.indexOf('http://') === 0 || raw.indexOf('https://') === 0 || raw.indexOf('/') === 0) return raw;
        if (raw.indexOf('./') === 0) return '../' + raw.slice(2);
        if (raw.indexOf('../') === 0) return '../' + raw;
        return '../' + raw;
      }

      var englishInsightCache = {};

      function normalizeEnglishReportHref(href){
        if (!href) return '';
        if (/index_en\\.html(\\?[^#]*)?(#.*)?$/i.test(href)) return href;
        if (/index\\.html(\\?[^#]*)?(#.*)?$/i.test(href)) {
          return href.replace(/index\\.html(\\?[^#]*)?(#.*)?$/i, 'index_en.html$1$2');
        }
        return href;
      }

      function stripTagText(raw){
        return String(raw || '')
          .replace(/<[^>]+>/g, ' ')
          .replace(/&nbsp;/g, ' ')
          .replace(/&amp;/g, '&')
          .replace(/&lt;/g, '<')
          .replace(/&gt;/g, '>')
          .replace(/&quot;/g, '"')
          .replace(/&#39;/g, "'")
          .replace(/\\s+/g, ' ')
          .trim();
      }

      function extractInsightItemsFromReportHtml(html){
        var m =
          html.match(/<h3[^>]*class="[^"]*key-insight-banner[^"]*"[^>]*>[\\s\\S]*?<\\/h3>\\s*<ul>([\\s\\S]*?)<\\/ul>/i) ||
          html.match(/<h3[^>]*>\\s*Key Insights?\\s*<\\/h3>\\s*<ul>([\\s\\S]*?)<\\/ul>/i);
        if (!m) return [];
        var out = [];
        var liMatches = m[1].matchAll(/<li[^>]*>([\\s\\S]*?)<\\/li>/gi);
        for (var li of liMatches) {
          var text = stripTagText(li[1]);
          if (!text) continue;
          if (/translatedtranslated/i.test(text)) continue;
          var translatedHits = (text.match(/\\btranslated\\b/gi) || []).length;
          if (translatedHits >= 3) continue;
          out.push(text);
          if (out.length >= 3) break;
        }
        return out;
      }

      function getEnglishInsightsForWeek(w){
        if (!isEnglishPage || !w || !w.week) return Promise.resolve([]);
        if (englishInsightCache[w.week]) return Promise.resolve(englishInsightCache[w.week]);

        var links = w.links || {};
        var htmlHref = resolveLinkFromHub(links.html, '../' + w.week + '/index_en.html');
        htmlHref = normalizeEnglishReportHref(htmlHref);
        if (!htmlHref) return Promise.resolve([]);

        return fetch(htmlHref, { credentials: 'same-origin' })
          .then(function(res){
            if (!res.ok) throw new Error('http_' + res.status);
            return res.text();
          })
          .then(function(html){
            var items = extractInsightItemsFromReportHtml(html);
            englishInsightCache[w.week] = items;
            return items;
          })
          .catch(function(){
            englishInsightCache[w.week] = [];
            return [];
          });
      }

      function buildInsightListHtml(items, limit){
        var safeItems = (items || [])
          .filter(function(t){ return !/\\btranslated\\b/i.test(String(t || '')); })
          .slice(0, limit || 2);
        if (!safeItems.length) return '<li>Open report for full insight details in English.</li>';
        return safeItems
          .map(function(t){ return '<li>' + String(t).replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</li>'; })
          .join('');
      }

      function hydrateEnglishInsightPreviews(){
        if (!isEnglishPage) return;

        var latest = weeks[0];
        if (latest) {
          getEnglishInsightsForWeek(latest).then(function(items){
            if (!items.length) return;
            var heroList = document.querySelector('#latestIssue .hero-insight ul');
            if (heroList) heroList.innerHTML = buildInsightListHtml(items, 3);
          });
        }

        var cards = Array.from(document.querySelectorAll('.week-card[data-week]'));
        cards.forEach(function(card){
          var week = card.getAttribute('data-week');
          if (!week) return;
          var targetWeek = getWeek(week);
          if (!targetWeek) return;
          getEnglishInsightsForWeek(targetWeek).then(function(items){
            if (!items.length) return;
            var ul = card.querySelector('.insight-mini ul');
            if (ul) ul.innerHTML = buildInsightListHtml(items, 2);
          });
        });
      }

      function buildCardHtml(w, idx, prevWeek){
        var links = w.links || {};
        var htmlLink = resolveLinkFromHub(links.html, '../' + w.week + '/index.html');
        var pdfLink = resolveLinkFromHub(links.pdf, '#');
        var m = w.metrics || {};
        var pm = prevWeek && prevWeek.metrics ? prevWeek.metrics : {};
        var badge = idx === 0 ? 'Latest' : ('W-' + idx);
        var insights = Array.isArray(w.executive_key_insights) ? w.executive_key_insights.slice(0, 2) : [];
        var insightItems = insights.length
          ? insights.map(function(t){ return '<li>' + localizeInsightText(t) + '</li>'; }).join('')
          : '<li>' + (isEnglishPage ? 'Open report for full insight details in English.' : 'Open report to view insights') + '</li>';

        function badgeDelta(cur, prev){
          if (typeof cur !== 'number' || typeof prev !== 'number') return '';
          var d = cur - prev;
          if (d === 0) return '';
          return ' <span class="delta-sm">' + (d > 0 ? '+' + d : '' + d) + '</span>';
        }

        return '' +
          '<div class="timeline-card' + (idx === 0 ? ' latest' : '') + '">' +
          '<article class="week-card" data-week="' + w.week + '" data-month="' + (w.week || '').slice(0,7) + '">' +
            '<div class="head"><div class="week">' + w.week + '</div><span class="badge">' + badge + '</span></div>' +
            '<div class="period">' + (isEnglishPage ? 'Period: ' : '기간: ') + (w.report_period && w.report_period.start ? w.report_period.start : '-') + ' ~ ' + (w.report_period && w.report_period.end ? w.report_period.end : '-') + '</div>' +
            '<div class="metric-badges">' +
              '<span class="metric-badge critical">Critical ' + (m.critical_country_count ?? '-') + badgeDelta(m.critical_country_count, pm.critical_country_count) + '</span>' +
              '<span class="metric-badge lg">LG ' + (m.lg_promotion_signals ?? '-') + badgeDelta(m.lg_promotion_signals, pm.lg_promotion_signals) + '</span>' +
              '<span class="metric-badge comp">Comp ' + (m.competitor_promotion_signals ?? '-') + badgeDelta(m.competitor_promotion_signals, pm.competitor_promotion_signals) + '</span>' +
              '<span class="metric-badge china">China ' + (m.chinese_threat_signals ?? '-') + badgeDelta(m.chinese_threat_signals, pm.chinese_threat_signals) + '</span>' +
            '</div>' +
            '<div class="insight-bubble"><div class="mini-title">💡 Key Insight</div><ul>' + insightItems + '</ul></div>' +
            '<div class="links">' +
              '<a class="btn primary" href="' + htmlLink + '">Report</a>' +
              '<a class="btn" href="' + pdfLink + '">PDF</a>' +
            '</div>' +
          '</article>' +
          '</div>';
      }

      function computeCadence(list){
        if (!list || list.length < 2) return null;
        var diffs = [];
        for (var i = 0; i < list.length - 1; i++) {
          var a = parseWeekDate(list[i].week);
          var b = parseWeekDate(list[i + 1].week);
          if (a && b) {
            var d = Math.round((a.getTime() - b.getTime()) / (1000 * 60 * 60 * 24));
            if (Number.isFinite(d) && d > 0) diffs.push(d);
          }
        }
        if (!diffs.length) return null;
        var sum = diffs.reduce(function(acc, cur){ return acc + cur; }, 0);
        return (sum / diffs.length).toFixed(1);
      }

      function updateArchiveStats(list){
        var el = document.getElementById('archiveStats');
        if (!el || !list.length) return;
        var dates = list.map(function(w){ return parseWeekDate(w.week); }).filter(Boolean).sort(function(a,b){ return a.getTime() - b.getTime(); });
        var oldest = dates[0];
        var latest = dates[dates.length - 1];
        var cadence = computeCadence(list);

        var range = (oldest && latest)
          ? oldest.toISOString().slice(0,10) + ' ~ ' + latest.toISOString().slice(0,10)
          : '-';

        el.innerHTML = '' +
          '<span>누적 주차: <strong>' + list.length + '</strong></span>' +
          '<span>날짜 범위: <strong>' + range + '</strong></span>' +
          '<span>평균 간격: <strong>' + (cadence ? cadence + '일' : '-') + '</strong></span>';
      }

      function groupByMonth(list){
        var groups = {};
        list.forEach(function(w){
          var month = (w.week || '').slice(0,7) || 'Unknown';
          if (!groups[month]) groups[month] = [];
          groups[month].push(w);
        });
        return groups;
      }

      function renderArchive(){
        if (!weekList) return;

        var sort = archiveSort ? archiveSort.value : 'desc';
        var groupMode = archiveGroup ? archiveGroup.value : 'month';

        var filtered = weeks.slice();

        filtered.sort(function(a,b){
          var da = parseWeekDate(a.week);
          var db = parseWeekDate(b.week);
          var base = 0;
          if (!da && !db) base = 0;
          else if (!da) base = 1;
          else if (!db) base = -1;
          else base = db.getTime() - da.getTime();
          return sort === 'asc' ? -base : base;
        });

        updateArchiveStats(filtered);

        if (!filtered.length) {
          weekList.innerHTML = '<div class="week-card">검색 결과가 없습니다.</div>';
          return;
        }

        function findPrev(w){
          var sorted = weeks.slice().sort(function(a,b){
            var da = parseWeekDate(a.week), db = parseWeekDate(b.week);
            if (!da && !db) return 0; if (!da) return 1; if (!db) return -1;
            return db.getTime() - da.getTime();
          });
          for (var i = 0; i < sorted.length; i++){
            if (sorted[i].week === w.week && i + 1 < sorted.length) return sorted[i+1];
          }
          return null;
        }

        if (groupMode === 'flat') {
          weekList.innerHTML = filtered.map(function(w, idx){ return buildCardHtml(w, idx, findPrev(w)); }).join('');
          hydrateEnglishInsightPreviews();
          return;
        }

        var grouped = groupByMonth(filtered);
        var months = Object.keys(grouped).sort(function(a,b){ return sort === 'asc' ? a.localeCompare(b) : b.localeCompare(a); });
        weekList.innerHTML = months.map(function(month){
          var items = grouped[month];
          var cards = items.map(function(w, idx){ return buildCardHtml(w, idx, findPrev(w)); }).join('');
          return '' +
            '<details class="month-group" open>' +
              '<summary>' + month + '<span class="month-meta">(' + items.length + ' reports)</span></summary>' +
              '<div class="week-list timeline-list" style="margin-top:8px">' + cards + '</div>' +
            '</details>';
        }).join('');
        hydrateEnglishInsightPreviews();
      }

      function safeCopy(url){
        var absoluteUrl;
        try { absoluteUrl = new URL(url, window.location.href).href; }
        catch (_) { absoluteUrl = url; }

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(absoluteUrl).then(function(){
            window.alert('링크가 복사되었습니다.');
          }).catch(function(){
            window.prompt('복사할 링크입니다:', absoluteUrl);
          });
          return;
        }
        window.prompt('복사할 링크입니다:', absoluteUrl);
      }

      function renderKpi(w){
        var m = (w && w.metrics) || {};
        var cards = [
          ['Covered Countries', m.covered_countries],
          ['Critical Countries', m.critical_country_count],
          ['LG Promotion Signals', m.lg_promotion_signals],
          ['Competitor Promotion Signals', m.competitor_promotion_signals],
          ['China Threat Signals', m.chinese_threat_signals]
        ].map(function(it){
          return '<div class="kpi"><div class="label">' + (it[0] ?? '-') + '</div><div class="value">' + (it[1] ?? '-') + '</div></div>';
        }).join('');
        document.getElementById('kpiRow').innerHTML = cards;
      }

      function chartDims(svg, minWidth, height){
        var width = Math.max(minWidth, Math.floor(svg.clientWidth || svg.getBoundingClientRect().width || minWidth));
        svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
        return { w: width, h: height, p: { l: 44, r: 12, t: 16, b: 28 } };
      }

      function drawTrendChart(){
        var svg = document.getElementById('trendSvg');
        if (!svg) return;
        var ordered = weeks.slice().reverse();
        if (!ordered.length) { svg.innerHTML = ''; return; }

        var dims = chartDims(svg, 680, 260);
        var plotW = dims.w - dims.p.l - dims.p.r;
        var plotH = dims.h - dims.p.t - dims.p.b;

        var yMax = 1;
        chartSeries.forEach(function(series){
          ordered.forEach(function(w){
            var v = metricValue(w, series.key);
            if (v !== null) yMax = Math.max(yMax, v);
          });
        });

        function xAt(i){
          if (ordered.length <= 1) return dims.p.l + plotW / 2;
          return dims.p.l + (plotW * i / (ordered.length - 1));
        }

        function yAt(v){
          return dims.p.t + (plotH * (1 - (v / yMax)));
        }

        var out = [];
        out.push('<line x1="' + dims.p.l + '" y1="' + dims.p.t + '" x2="' + dims.p.l + '" y2="' + (dims.h - dims.p.b) + '" stroke="#9fb3c8" stroke-width="1"/>');
        out.push('<line x1="' + dims.p.l + '" y1="' + (dims.h - dims.p.b) + '" x2="' + (dims.w - dims.p.r) + '" y2="' + (dims.h - dims.p.b) + '" stroke="#9fb3c8" stroke-width="1"/>');

        for (var t = 0; t <= 4; t++) {
          var vTick = yMax * t / 4;
          var yTick = yAt(vTick);
          out.push('<line x1="' + dims.p.l + '" y1="' + yTick + '" x2="' + (dims.w - dims.p.r) + '" y2="' + yTick + '" stroke="#eef3f8" stroke-width="1"/>');
          out.push('<text x="' + (dims.p.l - 8) + '" y="' + (yTick + 4) + '" text-anchor="end" font-size="11" fill="#64748b">' + Math.round(vTick) + '</text>');
        }

        chartSeries.forEach(function(series){
          var pts = [];
          ordered.forEach(function(w, i){
            var v = metricValue(w, series.key);
            if (v === null) return;
            pts.push({ x: xAt(i), y: yAt(v), v: v, week: w.week });
          });

          if (pts.length >= 2) {
            out.push('<polyline fill="none" stroke="' + series.color + '" stroke-width="2.2" points="' + pts.map(function(p){ return p.x + ',' + p.y; }).join(' ') + '"/>');
          }
          pts.forEach(function(p){
            out.push('<circle cx="' + p.x + '" cy="' + p.y + '" r="3.2" fill="' + series.color + '"><title>' + p.week + ': ' + p.v + '</title></circle>');
          });
        });

        var labelStep = ordered.length > 8 ? Math.ceil(ordered.length / 6) : 1;
        ordered.forEach(function(w, i){
          if (i % labelStep !== 0 && i !== ordered.length - 1) return;
          out.push('<text x="' + xAt(i) + '" y="' + (dims.h - 8) + '" text-anchor="middle" font-size="11" fill="#64748b">' + w.week.slice(5) + '</text>');
        });

        svg.innerHTML = out.join('');

        var legend = chartSeries.map(function(s){
          var cls = 'critical';
          if (s.key === 'lg_promotion_signals') cls = 'lg';
          if (s.key === 'competitor_promotion_signals') cls = 'comp';
          if (s.key === 'chinese_threat_signals') cls = 'china';
          return '<span class="legend-item"><span class="sw ' + cls + '"></span>' + s.label + '</span>';
        }).join('');
        document.getElementById('trendLegend').innerHTML = legend;
      }

      function drawCompareChart(A, B){
        var svg = document.getElementById('compareSvg');
        if (!svg) return;

        var dims = chartDims(svg, 680, 260);
        var plotW = dims.w - dims.p.l - dims.p.r;
        var plotH = dims.h - dims.p.t - dims.p.b;
        var bars = chartSeries;

        var yMax = 1;
        bars.forEach(function(series){
          var av = metricValue(A, series.key);
          var bv = metricValue(B, series.key);
          if (av !== null) yMax = Math.max(yMax, av);
          if (bv !== null) yMax = Math.max(yMax, bv);
        });

        function yAt(v){ return dims.p.t + (plotH * (1 - (v / yMax))); }

        var out = [];
        out.push('<line x1="' + dims.p.l + '" y1="' + dims.p.t + '" x2="' + dims.p.l + '" y2="' + (dims.h - dims.p.b) + '" stroke="#9fb3c8" stroke-width="1"/>');
        out.push('<line x1="' + dims.p.l + '" y1="' + (dims.h - dims.p.b) + '" x2="' + (dims.w - dims.p.r) + '" y2="' + (dims.h - dims.p.b) + '" stroke="#9fb3c8" stroke-width="1"/>');

        for (var t = 0; t <= 4; t++) {
          var vTick = yMax * t / 4;
          var yTick = yAt(vTick);
          out.push('<line x1="' + dims.p.l + '" y1="' + yTick + '" x2="' + (dims.w - dims.p.r) + '" y2="' + yTick + '" stroke="#eef3f8" stroke-width="1"/>');
          out.push('<text x="' + (dims.p.l - 8) + '" y="' + (yTick + 4) + '" text-anchor="end" font-size="11" fill="#64748b">' + Math.round(vTick) + '</text>');
        }

        var groupW = plotW / bars.length;
        var barW = Math.min(24, Math.max(12, groupW * 0.24));
        bars.forEach(function(series, i){
          var center = dims.p.l + (groupW * i) + (groupW / 2);
          var av = metricValue(A, series.key);
          var bv = metricValue(B, series.key);

          if (av !== null) {
            var yA = yAt(av);
            var hA = Math.max(0, (dims.h - dims.p.b) - yA);
            out.push('<rect x="' + (center - barW - 3) + '" y="' + yA + '" width="' + barW + '" height="' + hA + '" fill="#0a7ac4"><title>A: ' + av + '</title></rect>');
            out.push('<text x="' + (center - barW / 2 - 3) + '" y="' + (yA - 4) + '" text-anchor="middle" font-size="10" fill="#0a7ac4">' + av + '</text>');
          }
          if (bv !== null) {
            var yB = yAt(bv);
            var hB = Math.max(0, (dims.h - dims.p.b) - yB);
            out.push('<rect x="' + (center + 3) + '" y="' + yB + '" width="' + barW + '" height="' + hB + '" fill="#334155"><title>B: ' + bv + '</title></rect>');
            out.push('<text x="' + (center + barW / 2 + 3) + '" y="' + (yB - 4) + '" text-anchor="middle" font-size="10" fill="#334155">' + bv + '</text>');
          }

          out.push('<text x="' + center + '" y="' + (dims.h - 8) + '" text-anchor="middle" font-size="11" fill="#64748b">' + series.label + '</text>');
        });

        svg.innerHTML = out.join('');
        var aWeek = A && A.week ? A.week : '-';
        var bWeek = B && B.week ? B.week : '-';
        document.getElementById('compareLegend').innerHTML =
          '<span class="legend-item"><span class="sw a"></span>A (' + aWeek + ')</span>' +
          '<span class="legend-item"><span class="sw b"></span>B (' + bWeek + ')</span>';
      }

      function renderCompare(){
        var weekAEl = document.getElementById('weekA');
        var weekBEl = document.getElementById('weekB');
        if (!weekAEl || !weekBEl) return;

        var weekA = weekAEl.value;
        var weekB = weekBEl.value;
        var A = getWeek(weekA);
        var B = getWeek(weekB);

        renderKpi(A);

        var rows = metricsConfig.map(function(cfg){
          var key = cfg[0];
          var label = cfg[1];
          var a = A && A.metrics ? A.metrics[key] : null;
          var b = B && B.metrics ? B.metrics[key] : null;
          var d = (typeof a === 'number' && typeof b === 'number') ? (a - b) : null;
          return '<tr>' +
            '<td>' + label + '</td>' +
            '<td>' + (a ?? '-') + '</td>' +
            '<td>' + (b ?? '-') + '</td>' +
            '<td class="delta ' + deltaCls(d) + '">' + fmtDelta(d) + '</td>' +
            '</tr>';
        }).join('');

        document.getElementById('compareBody').innerHTML = rows;
        drawCompareChart(A, B);
      }

      document.addEventListener('click', function(e){
        var t = e.target;
        if (!t || !t.classList || !t.classList.contains('copy')) return;
        var url = t.getAttribute('data-copy-url');
        if (url) safeCopy(url);
      });

      if (archiveSort) archiveSort.addEventListener('change', renderArchive);
      if (archiveGroup) archiveGroup.addEventListener('change', renderArchive);

      var weekAEl = document.getElementById('weekA');
      var weekBEl = document.getElementById('weekB');
      if (weekAEl) weekAEl.addEventListener('change', renderCompare);
      if (weekBEl) weekBEl.addEventListener('change', renderCompare);

      window.addEventListener('resize', function(){
        drawTrendChart();
        renderCompare();
      });

      drawTrendChart();
      renderArchive();
      renderCompare();
      hydrateEnglishInsightPreviews();
    })();
  </script>
  <script>
  (function(){
    try {
      var m = JSON.parse(document.getElementById('manifest-data').textContent || '{"weeks":[]}');
      var weeks = (m.weeks || []).slice();
      weeks.sort(function(a,b){ return (a.week||'').localeCompare(b.week||''); });
      var series = [
        {key:'critical_country_count', label:'Critical', color:'#b91c1c'},
        {key:'lg_promotion_signals', label:'LG Promo', color:'#0a7ac4'},
        {key:'competitor_promotion_signals', label:'Comp Promo', color:'#b45309'},
        {key:'chinese_threat_signals', label:'China Threat', color:'#166534'}
      ];
      var svg = document.getElementById('trendSvg');
      if (svg && weeks.length) {
        var W=700,H=260,pl=50,pr=12,pt=20,pb=30,pw=W-pl-pr,ph=H-pt-pb;
        var yMax=1;
        series.forEach(function(s){weeks.forEach(function(w){var v=w.metrics?w.metrics[s.key]:null;if(typeof v==='number')yMax=Math.max(yMax,v)})});
        yMax=Math.ceil(yMax*1.1);
        function xAt(i){return weeks.length<=1?pl+pw/2:pl+(pw*i/(weeks.length-1))}
        function yAt(v){return pt+(ph*(1-(v/yMax)))}
        var o=[];
        for(var t=0;t<=4;t++){var vT=yMax*t/4,yT=yAt(vT);o.push('<line x1="'+pl+'" y1="'+yT+'" x2="'+(W-pr)+'" y2="'+yT+'" stroke="#eef3f8"/>');o.push('<text x="'+(pl-8)+'" y="'+(yT+4)+'" text-anchor="end" font-size="11" fill="#64748b">'+Math.round(vT)+'</text>')}
        series.forEach(function(s){var pts=[];weeks.forEach(function(w,i){var v=w.metrics?w.metrics[s.key]:null;if(typeof v==='number')pts.push({x:xAt(i),y:yAt(v),v:v})});if(pts.length>=2)o.push('<polyline fill="none" stroke="'+s.color+'" stroke-width="2.5" points="'+pts.map(function(p){return p.x+','+p.y}).join(' ')+'"/>');pts.forEach(function(p){o.push('<circle cx="'+p.x+'" cy="'+p.y+'" r="4" fill="'+s.color+'"><title>'+s.label+': '+p.v+'</title></circle>')})});
        weeks.forEach(function(w,i){o.push('<text x="'+xAt(i)+'" y="'+(H-8)+'" text-anchor="middle" font-size="11" fill="#64748b">'+w.week.slice(5)+'</text>')});
        svg.setAttribute('viewBox','0 0 '+W+' '+H);svg.innerHTML=o.join('');
        var leg=document.getElementById('trendLegend');
        if(leg)leg.innerHTML=series.map(function(s){return '<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;font-size:12px"><span style="width:10px;height:10px;border-radius:50%;background:'+s.color+';display:inline-block"></span>'+s.label+'</span>'}).join('');
      }
      var weekAEl=document.getElementById('weekA'),weekBEl=document.getElementById('weekB'),compareSvg=document.getElementById('compareSvg'),compareBody=document.getElementById('compareBody'),compareLeg=document.getElementById('compareLegend');
      function getW(wk){return weeks.find(function(w){return w.week===wk})}
      function drawCompare(){
        if(!weekAEl||!weekBEl||!compareSvg)return;
        var A=getW(weekAEl.value),B=getW(weekBEl.value);if(!A||!B)return;
        if(compareBody){var mc=[['covered_countries','커버 국가 수'],['critical_country_count','Critical 국가 수'],['lg_promotion_signals','LG 프로모션 신호'],['competitor_promotion_signals','경쟁사 공격 프로모션'],['chinese_threat_signals','중국 브랜드 위협 신호'],['consumer_negative_countries','Consumer Negative 국가 수']];compareBody.innerHTML=mc.map(function(c){var a=A.metrics?A.metrics[c[0]]:null,b=B.metrics?B.metrics[c[0]]:null,d=(typeof a==='number'&&typeof b==='number')?(a-b):null;var cls=d===null?'':d>0?' style="color:#166534;font-weight:700"':d<0?' style="color:#b91c1c;font-weight:700"':'';return '<tr><td>'+c[1]+'</td><td>'+(a!=null?a:'-')+'</td><td>'+(b!=null?b:'-')+'</td><td'+cls+'>'+(d===null?'-':d>0?'+'+d:''+d)+'</td></tr>'}).join('')}
        var W2=700,H2=260,pl2=50,pr2=12,pt2=20,pb2=30,pw2=W2-pl2-pr2,ph2=H2-pt2-pb2,yMax2=1;
        series.forEach(function(s){var av=A.metrics?A.metrics[s.key]:0,bv=B.metrics?B.metrics[s.key]:0;yMax2=Math.max(yMax2,av,bv)});yMax2=Math.ceil(yMax2*1.1);
        function yAt2(v){return pt2+(ph2*(1-(v/yMax2)))}
        var o2=[];for(var t=0;t<=4;t++){var vT=yMax2*t/4,yT=yAt2(vT);o2.push('<line x1="'+pl2+'" y1="'+yT+'" x2="'+(W2-pr2)+'" y2="'+yT+'" stroke="#eef3f8"/>');o2.push('<text x="'+(pl2-8)+'" y="'+(yT+4)+'" text-anchor="end" font-size="11" fill="#64748b">'+Math.round(vT)+'</text>')}
        var gw=pw2/series.length,bw=Math.min(28,gw*0.3);
        series.forEach(function(s,i){var cx=pl2+(gw*i)+(gw/2);var av=A.metrics?A.metrics[s.key]:0,bv=B.metrics?B.metrics[s.key]:0;var yA=yAt2(av),hA=Math.max(0,(H2-pb2)-yA),yB=yAt2(bv),hB=Math.max(0,(H2-pb2)-yB);o2.push('<rect x="'+(cx-bw-2)+'" y="'+yA+'" width="'+bw+'" height="'+hA+'" fill="#0a7ac4" rx="2"><title>A: '+av+'</title></rect>');o2.push('<text x="'+(cx-bw/2-2)+'" y="'+(yA-4)+'" text-anchor="middle" font-size="10" fill="#0a7ac4">'+av+'</text>');o2.push('<rect x="'+(cx+2)+'" y="'+yB+'" width="'+bw+'" height="'+hB+'" fill="#334155" rx="2"><title>B: '+bv+'</title></rect>');o2.push('<text x="'+(cx+bw/2+2)+'" y="'+(yB-4)+'" text-anchor="middle" font-size="10" fill="#334155">'+bv+'</text>');o2.push('<text x="'+cx+'" y="'+(H2-8)+'" text-anchor="middle" font-size="10" fill="#64748b">'+s.label+'</text>')});
        compareSvg.setAttribute('viewBox','0 0 '+W2+' '+H2);compareSvg.innerHTML=o2.join('');
        if(compareLeg)compareLeg.innerHTML='<span style="display:inline-flex;align-items:center;gap:4px;margin-right:12px;font-size:12px"><span style="width:10px;height:10px;border-radius:50%;background:#0a7ac4;display:inline-block"></span>A ('+A.week+')</span><span style="display:inline-flex;align-items:center;gap:4px;font-size:12px"><span style="width:10px;height:10px;border-radius:50%;background:#334155;display:inline-block"></span>B ('+B.week+')</span>';
      }
      drawCompare();
      if(weekAEl)weekAEl.addEventListener('change',drawCompare);
      if(weekBEl)weekBEl.addEventListener('change',drawCompare);
      window.addEventListener('resize',function(){drawCompare()});
    } catch(e){console.error('Chart error:',e)}
  })();
  </script>
</body>
</html>`;

  const outPath = path.resolve(outputHtml);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, html, 'utf8');
  console.log(`Hub written: ${outPath}`);

  if (path.basename(outPath) === 'hub.html') {
    const outEnPath = path.join(path.dirname(outPath), 'hub_en.html');
  const enHtml = buildEnglishHubHtml(html, weeks, outputHtml);
    fs.writeFileSync(outEnPath, enHtml, 'utf8');
    console.log(`Hub EN written: ${outEnPath}`);
  }
}

main();
