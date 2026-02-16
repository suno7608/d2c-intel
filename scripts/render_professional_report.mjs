#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderInline(text) {
  let out = escapeHtml(text);
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  return out;
}

function isSpecialLine(line) {
  return (
    /^#{1,6}\s+/.test(line) ||
    /^\|/.test(line) ||
    /^[-*]\s+/.test(line) ||
    /^\d+\.\s+/.test(line) ||
    /^>\s?/.test(line) ||
    /^---+\s*$/.test(line)
  );
}

function isTableSeparator(line) {
  return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function parseTableRow(row) {
  let t = row.trim();
  if (t.startsWith('|')) t = t.slice(1);
  if (t.endsWith('|')) t = t.slice(0, -1);
  return t.split('|').map((c) => renderInline(c.trim()));
}

function resolveTocLevel(headingLevel, headingText) {
  const text = String(headingText || '').trim();
  if (headingLevel === 2) {
    // Keep Appendix as top-level.
    if (/^appendix\b/i.test(text)) return 2;
    // 3.1 / 3.2 style headings should be visually nested under their parent section.
    if (/^\d+\.\d+(\.\d+)?\b/.test(text)) return 3;
    return 2;
  }
  if (headingLevel === 3) {
    if (/^\d+\.\d+\.\d+\b/.test(text)) return 4;
    return 3;
  }
  return headingLevel;
}

function localizeHeadingText(text) {
  let out = String(text || '').trim();
  const replacements = [
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
    [/Appendix C:\s*Glossary/gi, '부록 C: 용어집']
  ];

  replacements.forEach(([pattern, next]) => {
    out = out.replace(pattern, next);
  });
  out = out.replace(/16개국/g, '핵심 법인');
  out = out.replace(/16-country/gi, '핵심 법인');
  return out;
}

function localizeTocText(text) {
  return localizeHeadingText(text);
}

function parseMarkdown(md, opts = {}) {
  const lang = opts.lang === 'en' ? 'en' : 'ko';
  const lines = md.replace(/\r\n/g, '\n').split('\n');
  const html = [];
  const toc = [];
  let headingCount = 0;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i += 1;
      continue;
    }

    if (/^---+\s*$/.test(line)) {
      html.push('<hr class="section-divider" />');
      i += 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text = headingMatch[2].trim();
      const localizedText = lang === 'ko' ? localizeHeadingText(text) : text;
      headingCount += 1;
      const id = `sec-${headingCount}`;
      const isKeyInsightHeading =
        level === 3 &&
        /^(key insight|핵심 인사이트)$/i.test(text.trim());
      const isActionRequiredHeading =
        level === 3 &&
        /^(action required|실행 필요)$/i.test(text.trim());
      const headingClass = level === 1 ? 'report-title' : level === 2 ? 'section-title' : 'sub-title';
      const headingClasses = [headingClass];
      if (isKeyInsightHeading) headingClasses.push('key-insight-banner');
      if (isActionRequiredHeading) headingClasses.push('action-required-banner');
      html.push(`<h${level} id="${id}" class="${headingClasses.join(' ')}">${renderInline(localizedText)}</h${level}>`);
      const isTocExcludedSubHeading =
        level === 3 &&
        /^(key insight|action required|핵심 인사이트|실행 필요)$/i.test(text.trim());
      if (level >= 2 && level <= 3 && !isTocExcludedSubHeading) {
        const tocText = lang === 'ko' ? localizeTocText(localizedText) : localizedText;
        toc.push({ level: resolveTocLevel(level, localizedText), text: tocText, id });
      }
      i += 1;
      continue;
    }

    if (/^\|/.test(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const header = parseTableRow(lines[i]);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i])) {
        rows.push(parseTableRow(lines[i]));
        i += 1;
      }

      const tableHead = `<thead><tr>${header.map((h) => `<th>${h}</th>`).join('')}</tr></thead>`;
      const tableBody = `<tbody>${rows
        .map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join('')}</tr>`)
        .join('')}</tbody>`;
      html.push(`<div class="table-wrap"><table>${tableHead}${tableBody}</table></div>`);
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s+/, ''));
        i += 1;
      }
      html.push(`<ul>${items.map((it) => `<li>${renderInline(it)}</li>`).join('')}</ul>`);
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ''));
        i += 1;
      }
      html.push(`<ol>${items.map((it) => `<li>${renderInline(it)}</li>`).join('')}</ol>`);
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quotes = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) {
        quotes.push(lines[i].replace(/^>\s?/, ''));
        i += 1;
      }
      html.push(`<blockquote>${renderInline(quotes.join(' '))}</blockquote>`);
      continue;
    }

    const para = [];
    while (i < lines.length && lines[i].trim() && !isSpecialLine(lines[i])) {
      para.push(lines[i].trim());
      i += 1;
    }
    html.push(`<p>${renderInline(para.join(' '))}</p>`);
  }

  return { body: html.join('\n'), toc };
}

function buildHtml({ title, subtitle, period, body, toc, lang }) {
  const htmlLang = lang === 'en' ? 'en' : 'ko';
  const tocTitle = lang === 'en' ? 'Quick Navigation' : '바로가기 메뉴';
  const periodLabel = lang === 'en' ? 'Report Period' : '보고 기간';
  const tocHtml = toc
    .map((t) => `<li class="l${t.level}"><a href="#${t.id}">${escapeHtml(t.text)}</a></li>`)
    .join('');

  return `<!doctype html>
<html lang="${htmlLang}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${escapeHtml(title)}</title>
  <style>
    :root {
      --bg: #f6f8fb;
      --paper: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --line: #dbe2ea;
      --brand: #005a9c;
      --alert: #b91c1c;
      --warn: #a16207;
      --ok: #166534;
      --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; background: var(--bg); color: var(--ink); }
    body { font: 15px/1.6 "Noto Sans KR", "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }

    .layout {
      display: grid;
      grid-template-columns: 290px minmax(0, 1fr);
      gap: 22px;
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
    }

    .toc-panel {
      position: sticky;
      top: 18px;
      align-self: start;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      box-shadow: var(--shadow);
      max-height: calc(100vh - 36px);
      overflow: auto;
    }
    .toc-title {
      margin: 0 0 10px;
      padding: 10px 11px;
      border-radius: 10px;
      background: linear-gradient(95deg, #003a66 0%, #005a9c 58%, #0a7ac4 100%);
      color: #fff;
      font-size: 13px;
      font-weight: 800;
      letter-spacing: 0.2px;
    }
    .toc-panel ul {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 6px;
    }
    .toc-panel li { margin: 0; }
    .toc-panel a {
      display: block;
      color: #0b4f88;
      text-decoration: none;
      border: 1px solid transparent;
      border-radius: 9px;
      background: #f8fbff;
      padding: 7px 10px;
      font-size: 13px;
      line-height: 1.35;
      transition: background-color .12s ease, border-color .12s ease, transform .12s ease;
    }
    .toc-panel a:hover {
      background: #edf5ff;
      border-color: #d5e5f6;
      transform: translateX(1px);
    }
    .toc-panel a:focus-visible {
      outline: 3px solid rgba(10,122,196,.35);
      outline-offset: 1px;
    }
    .toc-panel li.l3 a {
      margin-left: 12px;
      background: #fcfdff;
      color: #28435f;
    }
    .toc-panel li.l4 a {
      margin-left: 24px;
      background: #ffffff;
      color: #3f5871;
      font-size: 12px;
    }
    .toc-panel a.is-active {
      background: #e5f1ff;
      border-color: #c9ddf3;
      color: #0b4f88;
      font-weight: 800;
    }

    .paper {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .cover {
      background: linear-gradient(140deg, #003a66, #005a9c 55%, #0a7ac4);
      color: #fff;
      padding: 34px 36px;
    }
    .cover h1 { margin: 0 0 8px; font-size: 34px; line-height: 1.2; font-weight: 800; }
    .cover p { margin: 6px 0; opacity: .95; }
    .cover .meta { margin-top: 14px; font-size: 14px; opacity: .92; }

    .content { padding: 30px 34px 38px; }
    .report-title { margin-top: 8px; font-size: 30px; line-height: 1.25; }
    .section-title {
      margin: 30px 0 12px;
      font-size: 22px;
      color: #fff;
      border-left: 0;
      padding: 12px 14px;
      border-radius: 12px;
      background: linear-gradient(95deg, #003a66 0%, #005a9c 58%, #0a7ac4 100%);
      box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
      letter-spacing: 0.1px;
      line-height: 1.35;
    }
    .sub-title {
      margin: 20px 0 10px;
      font-size: 17px;
      color: #0b3354;
      border: 1px solid #cfe0f1;
      border-radius: 10px;
      padding: 9px 12px;
      background: linear-gradient(120deg, #f8fbff 0%, #eef5fd 100%);
      box-shadow: 0 4px 10px rgba(15, 23, 42, 0.06);
      line-height: 1.35;
    }
    .sub-title.key-insight-banner {
      border-color: #d1e4f7;
      background: linear-gradient(120deg, #eff7ff 0%, #e5f1ff 100%);
      color: #0b4f88;
      font-weight: 800;
    }
    .sub-title.action-required-banner {
      border-color: #f1dfc4;
      background: linear-gradient(120deg, #fff8ea 0%, #ffefcf 100%);
      color: #8a4b00;
      font-weight: 800;
    }
    p { margin: 10px 0; }
    hr.section-divider { border: 0; border-top: 1px solid var(--line); margin: 18px 0; }

    blockquote {
      margin: 14px 0;
      padding: 10px 14px;
      border-left: 4px solid var(--brand);
      background: #eef6fc;
      color: #15324a;
    }

    a { color: var(--brand); text-decoration: none; }
    a:hover { text-decoration: underline; }

    ul, ol { margin: 8px 0 10px 22px; }

    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 12px;
      margin: 12px 0 18px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
      background: #fff;
      font-size: 14px;
    }
    th, td {
      border-bottom: 1px solid #e7edf4;
      border-right: 1px solid #eef3f8;
      padding: 8px 10px;
      vertical-align: top;
      text-align: left;
    }
    th:last-child, td:last-child { border-right: 0; }
    thead th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: #f1f7fd;
      color: #15324a;
      font-weight: 700;
    }

    code {
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 1px 5px;
      font-size: .92em;
    }

    .foot {
      border-top: 1px solid var(--line);
      color: var(--muted);
      padding: 14px 34px 24px;
      font-size: 13px;
    }

    @media (max-width: 1100px) {
      .layout { grid-template-columns: 1fr; padding: 14px; }
      .toc-panel { position: relative; top: 0; max-height: none; }
      .toc-title { margin-bottom: 8px; }
      .toc-panel li.l3 a,
      .toc-panel li.l4 a { margin-left: 0; }
      .cover h1 { font-size: 28px; }
      .content { padding: 20px 16px 28px; }
      .foot { padding: 14px 16px 22px; }
      .section-title { font-size: 20px; }
      .sub-title { font-size: 17px; }
    }

    @media print {
      body { background: #fff; }
      .layout { display: block; max-width: none; padding: 0; }
      .toc-panel { display: none; }
      .paper { border: none; box-shadow: none; }
      .cover { border-radius: 0; }
      .content { padding: 18mm 12mm 16mm; }
      .foot { padding: 8mm 12mm 0; }
      .section-title { break-after: avoid; }
      .section-title,
      .sub-title {
        background: #fff !important;
        color: #003a66 !important;
        border: 1px solid #cfd8e3 !important;
        box-shadow: none !important;
      }
      .table-wrap { break-inside: avoid; }
      a { color: #003a66; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="toc-panel">
      <div class="toc-title">${tocTitle}</div>
      <ul>${tocHtml}</ul>
    </aside>
    <main class="paper">
      <header class="cover">
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(subtitle)}</p>
        <p class="meta">${periodLabel}: ${escapeHtml(period)}</p>
      </header>
      <section class="content">
        ${body}
      </section>
      <footer class="foot">Generated for executive sharing · LG Global D2C Weekly Intelligence</footer>
    </main>
  </div>
  <script>
    (function () {
      const tocLinks = Array.from(document.querySelectorAll('.toc-panel a[href^="#"]'));
      if (!tocLinks.length) return;

      const linkById = new Map();
      tocLinks.forEach((link) => {
        const id = (link.getAttribute('href') || '').slice(1);
        if (id) linkById.set(id, link);
      });

      function setActive(id) {
        tocLinks.forEach((l) => l.classList.remove('is-active'));
        const target = linkById.get(id);
        if (target) target.classList.add('is-active');
      }

      const headings = Array.from(linkById.keys())
        .map((id) => document.getElementById(id))
        .filter(Boolean);

      if (!headings.length) return;
      setActive(headings[0].id);

      const observer = new IntersectionObserver(
        (entries) => {
          const visible = entries
            .filter((e) => e.isIntersecting)
            .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
          if (visible.length) setActive(visible[0].target.id);
        },
        { root: null, rootMargin: '-22% 0px -64% 0px', threshold: [0, 1] }
      );

      headings.forEach((h) => observer.observe(h));

      tocLinks.forEach((link) => {
        link.addEventListener('click', () => {
          const id = (link.getAttribute('href') || '').slice(1);
          if (id) setActive(id);
        });
      });
    })();
  </script>
</body>
</html>`;
}

function main() {
  const [, , inputFile, outputHtml, langArg] = process.argv;
  if (!inputFile || !outputHtml) {
    console.error('Usage: node render_professional_report.mjs <input.md> <output.html> [ko|en]');
    process.exit(1);
  }
  const lang = langArg === 'en' ? 'en' : 'ko';

  const absInput = path.resolve(inputFile);
  const absOutput = path.resolve(outputHtml);
  const md = fs.readFileSync(absInput, 'utf8');
  const { body, toc } = parseMarkdown(md, { lang });

  const title =
    lang === 'en'
      ? 'LG Electronics Global D2C Weekly Market Intelligence Report'
      : 'LG전자 글로벌 D2C 주간 시장 인텔리전스 리포트';
  const subtitle =
    lang === 'en'
      ? 'Consumer Sentiment · Retail Channel Promotion · Price Intelligence · Chinese Brand Tracking'
      : '소비자 반응 · 유통 채널 프로모션 · 가격 인텔리전스 · 중국 브랜드 동향';
  const periodMatch = md.match(/(?:Report Period|보고 기간):\s*([^\n]+)/);
  const period = periodMatch ? periodMatch[1].trim() : 'N/A';

  const html = buildHtml({ title, subtitle, period, body, toc, lang });
  fs.mkdirSync(path.dirname(absOutput), { recursive: true });
  fs.writeFileSync(absOutput, html, 'utf8');
  console.log(`HTML written: ${absOutput}`);
}

main();
