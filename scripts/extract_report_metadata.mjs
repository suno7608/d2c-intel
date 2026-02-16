#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function usage() {
  console.error('Usage: node extract_report_metadata.mjs <source_md> <date_key> <output_json>');
  process.exit(1);
}

function parseInteger(value, fallback = null) {
  if (!value) return fallback;
  const m = String(value).match(/-?\d+/);
  return m ? Number(m[0]) : fallback;
}

function normalizeLabel(text) {
  return String(text || '')
    .replace(/[`*]/g, '')
    .replace(/\s+/g, '')
    .replace(/[()]/g, '')
    .toLowerCase();
}

function parsePipeRow(line) {
  let t = String(line || '').trim();
  if (!t.startsWith('|')) return null;
  if (t.startsWith('|')) t = t.slice(1);
  if (t.endsWith('|')) t = t.slice(0, -1);
  const cells = t.split('|').map((c) => c.trim());
  return cells;
}

function isPipeSeparator(line) {
  return /^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(String(line || '').trim());
}

function extractPeriod(md) {
  const patterns = [
    /Report Period:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*[—-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})/i,
    /보고 기간:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*[—-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})/i,
  ];
  for (const p of patterns) {
    const m = md.match(p);
    if (m) return { start: m[1], end: m[2] };
  }
  return { start: null, end: null };
}

function extractVersion(md) {
  const m = md.match(/(?:Version|버전):\s*(.+)/i);
  return m ? m[1].trim() : null;
}

function extractExecutiveInsights(md) {
  const lines = md.split(/\r?\n/);
  const sec1Idx = lines.findIndex((l) => /^##\s*1\./.test(l));
  if (sec1Idx < 0) return [];

  let keyIdx = -1;
  for (let i = sec1Idx + 1; i < lines.length; i += 1) {
    if (/^##\s+/.test(lines[i])) break;
    if (/^###\s*(Key Insight|핵심 인사이트)\s*$/i.test(lines[i].trim())) {
      keyIdx = i;
      break;
    }
  }
  if (keyIdx < 0) return [];

  const out = [];
  for (let i = keyIdx + 1; i < lines.length; i += 1) {
    const line = lines[i].trim();
    if (/^###\s+/.test(line) || /^##\s+/.test(line)) break;
    if (line.startsWith('- ')) out.push(line.replace(/^-+\s+/, ''));
  }
  return out.slice(0, 4);
}

function findMetricValue(md, labelCandidates) {
  const labels = labelCandidates.map((x) => normalizeLabel(x));
  const lines = md.split(/\r?\n/);
  for (const line of lines) {
    if (!line.trim().startsWith('|') || isPipeSeparator(line)) continue;
    const cells = parsePipeRow(line);
    if (!cells || cells.length < 2) continue;
    const head = normalizeLabel(cells[0]);
    if (!labels.some((l) => head.includes(l))) continue;
    for (let i = 1; i < cells.length; i += 1) {
      const n = parseInteger(cells[i], null);
      if (n !== null) return n;
    }
  }
  return null;
}

function extractCriticalCountriesFromAlertMap(md) {
  const lines = md.split(/\r?\n/);
  const headingIdx = lines.findIndex(
    (l) => /^###\s*2\.1\b/.test(l.trim()) || /Alert Map|알림 맵/i.test(l),
  );
  if (headingIdx < 0) return [];

  let tableStart = -1;
  for (let i = headingIdx + 1; i < lines.length; i += 1) {
    if (/^###\s+/.test(lines[i]) || /^##\s+/.test(lines[i])) break;
    if (lines[i].trim().startsWith('|')) {
      tableStart = i;
      break;
    }
  }
  if (tableStart < 0) return [];

  const tableLines = [];
  for (let i = tableStart; i < lines.length; i += 1) {
    const t = lines[i].trim();
    if (!t.startsWith('|')) break;
    tableLines.push(t);
  }
  if (tableLines.length < 3) return [];

  const header = parsePipeRow(tableLines[0]) || [];
  let countryIdx = 0;
  let severityIdx = 2;
  header.forEach((h, i) => {
    const n = normalizeLabel(h);
    if (n.includes('country') || n.includes('국가')) countryIdx = i;
    if (n.includes('severity') || n.includes('심각') || n.includes('위험')) severityIdx = i;
  });

  const result = [];
  for (let i = 2; i < tableLines.length; i += 1) {
    if (isPipeSeparator(tableLines[i])) continue;
    const cells = parsePipeRow(tableLines[i]);
    if (!cells || cells.length <= Math.max(countryIdx, severityIdx)) continue;
    const severity = cells[severityIdx] || '';
    if (!/🔴|critical/i.test(severity)) continue;
    const country = (cells[countryIdx] || '').trim();
    if (country) result.push(country);
  }
  return Array.from(new Set(result));
}

function loadFallbackStats(dateKey) {
  try {
    const root = path.resolve(path.dirname(process.argv[1]), '..');
    const statsFile = path.join(root, 'data', 'weekly_stats', `${dateKey}.json`);
    const rawFile = path.join(root, 'data', 'raw', `openclaw_${dateKey}.jsonl`);

    let stats = null;
    if (fs.existsSync(statsFile)) {
      stats = JSON.parse(fs.readFileSync(statsFile, 'utf8'));
    }

    let rawRecords = [];
    if (fs.existsSync(rawFile)) {
      rawRecords = fs
        .readFileSync(rawFile, 'utf8')
        .split(/\r?\n/)
        .filter(Boolean)
        .map((line) => {
          try {
            return JSON.parse(line);
          } catch {
            return null;
          }
        })
        .filter(Boolean);
    }

    const competitorPromoCountries = new Set();
    const chineseCountries = new Set();
    const chineseBrands = new Set(['tcl', 'hisense', 'haier', 'midea']);
    for (const r of rawRecords) {
      const brand = String(r.brand || '').toLowerCase();
      const country = String(r.country || '').trim();
      const signalType = String(r.signal_type || '').toLowerCase();
      if (country && brand !== 'lg' && (signalType.includes('promo') || signalType.includes('discount'))) {
        competitorPromoCountries.add(country);
      }
      if (country && chineseBrands.has(brand)) chineseCountries.add(country);
    }

    return {
      coveredCountries: stats?.countries_count ?? null,
      lgPromotions: stats?.lg_promo_count ?? null,
      competitorPromotions: competitorPromoCountries.size || null,
      chineseThreatSignals: (stats?.chinese_countries_count ?? chineseCountries.size) || null,
      consumerNegative: stats?.consumer_negative_count ?? null,
    };
  } catch {
    return {
      coveredCountries: null,
      lgPromotions: null,
      competitorPromotions: null,
      chineseThreatSignals: null,
      consumerNegative: null,
    };
  }
}

function main() {
  const [, , sourceMd, dateKey, outputJson] = process.argv;
  if (!sourceMd || !dateKey || !outputJson) usage();

  const absMd = path.resolve(sourceMd);
  const absOut = path.resolve(outputJson);
  const md = fs.readFileSync(absMd, 'utf8');

  const period = extractPeriod(md);
  const version = extractVersion(md);
  const fallback = loadFallbackStats(dateKey);

  const covered = findMetricValue(md, ['커버된 국가 수', 'covered countries', 'countries covered']) ?? fallback.coveredCountries;
  const lgPromotions =
    findMetricValue(md, ['LG 프로모션 시그널', 'LG 프로모션 감지', 'LG Promotion Signals']) ?? fallback.lgPromotions;
  const competitorPromotions =
    findMetricValue(md, ['경쟁사 공격 프로모션 시그널', '경쟁사 공격적 프로모션 감지', 'Competitor Aggressive Promotions']) ??
    fallback.competitorPromotions;
  const chineseThreatSignals =
    findMetricValue(md, ['중국 브랜드 위협 시그널', '중국 브랜드 바이럴', 'China Brand Threat Signals']) ??
    fallback.chineseThreatSignals;
  const consumerNegativeCountries =
    findMetricValue(md, ['Consumer Negative Alert 국가', 'Consumer Negative Alert Countries']) ?? fallback.consumerNegative;

  const criticalCountries = extractCriticalCountriesFromAlertMap(md);
  const criticalCount =
    findMetricValue(md, ['Critical 국가', 'Critical Countries']) ??
    (criticalCountries.length ? criticalCountries.length : null);

  const payload = {
    week: dateKey,
    report_period: period,
    version,
    generated_at: new Date().toISOString(),
    metrics: {
      covered_countries: covered,
      lg_promotion_signals: lgPromotions,
      competitor_promotion_signals: competitorPromotions,
      chinese_threat_signals: chineseThreatSignals,
      consumer_negative_countries: consumerNegativeCountries,
      critical_country_count: criticalCount,
    },
    critical_countries: criticalCountries,
    executive_key_insights: extractExecutiveInsights(md),
    links: {
      html: `./${dateKey}/index.html`,
      pdf: `../pdf/LG_Global_D2C_Weekly_Intelligence_${dateKey}_R2_16country.pdf`,
      md: `../md/LG_Global_D2C_Weekly_Intelligence_${dateKey}_R2_16country.md`,
      share: `./${dateKey}/share.html`,
    },
  };

  fs.mkdirSync(path.dirname(absOut), { recursive: true });
  fs.writeFileSync(absOut, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(`Metadata written: ${absOut}`);
}

main();
