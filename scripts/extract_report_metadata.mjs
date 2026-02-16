#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function usage() {
  console.error('Usage: node extract_report_metadata.mjs <source_md> <date_key> <output_json>');
  process.exit(1);
}

function findTableRowCells(md, label) {
  const lines = md.split(/\r?\n/);
  for (const line of lines) {
    if (!line.startsWith('|')) continue;
    const raw = line.trim();
    if (/^\|\s*-/.test(raw)) continue;
    const parts = raw.split('|').map((x) => x.trim()).filter(Boolean);
    if (parts.length < 2) continue;
    if (parts[0] === label) return parts;
  }
  return null;
}

function parseInteger(value, fallback = null) {
  if (!value) return fallback;
  const m = String(value).match(/-?\d+/);
  return m ? Number(m[0]) : fallback;
}

function extractPeriod(md) {
  const m = md.match(/Report Period:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*[—-]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})/);
  return m ? { start: m[1], end: m[2] } : { start: null, end: null };
}

function extractVersion(md) {
  const m = md.match(/Version:\s*(.+)/);
  return m ? m[1].trim() : null;
}

function extractExecutiveInsights(md) {
  const block = md.match(/##\s*1\.\s*Executive Summary[\s\S]*?###\s*Key Insight\n([\s\S]*?)(?:\n###\s*1\.1|\n##\s*2\.)/);
  if (!block) return [];
  return block[1]
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.startsWith('- '))
    .map((l) => l.replace(/^-\s+/, ''))
    .slice(0, 4);
}

function extractCriticalCountries(md) {
  const row = findTableRowCells(md, 'Critical 국가');
  if (!row || row.length < 6) return [];
  const candidate = row[row.length - 2] || '';
  return candidate
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => x.replace(/\.$/, ''));
}

function main() {
  const [, , sourceMd, dateKey, outputJson] = process.argv;
  if (!sourceMd || !dateKey || !outputJson) usage();

  const absMd = path.resolve(sourceMd);
  const absOut = path.resolve(outputJson);
  const md = fs.readFileSync(absMd, 'utf8');

  const period = extractPeriod(md);
  const version = extractVersion(md);

  const covered = parseInteger(findTableRowCells(md, '커버된 국가 수')?.[1]);
  const lgPromotions = parseInteger(findTableRowCells(md, 'LG 프로모션 시그널(국가 단위)')?.[1]);
  const competitorPromotions = parseInteger(findTableRowCells(md, '경쟁사 공격 프로모션 시그널')?.[1]);
  const chineseThreatSignals = parseInteger(findTableRowCells(md, '중국 브랜드 위협 시그널')?.[1]);
  const consumerNegativeCountries = parseInteger(findTableRowCells(md, 'Consumer Negative Alert 국가')?.[1]);
  const criticalCount = parseInteger(findTableRowCells(md, 'Critical 국가(🔴)')?.[1]);

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
    critical_countries: extractCriticalCountries(md),
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
