/**
 * GET /api/regions  — LOCAL DEV VERSION
 * 로컬 파일시스템에서 직접 읽음 (GitHub 불필요)
 * local-dev-server.mjs 에서 이 파일을 우선 사용
 */

import fs   from 'fs';
import path from 'path';

const REPO_ROOT = process.cwd();

const REGION_META = {
  nam:   { id: 'nam',   name: '북미',         flag: '🌎', en: 'North America' },
  eur:   { id: 'eur',   name: '유럽',         flag: '🌍', en: 'Europe' },
  latam: { id: 'latam', name: '중남미',       flag: '🌎', en: 'Latin America' },
  asia:  { id: 'asia',  name: '아시아',       flag: '🌏', en: 'Asia Pacific' },
  mea:   { id: 'mea',   name: '중동·아프리카', flag: '🌍', en: 'Middle East & Africa' },
};

function readJSON(filePath) {
  if (!fs.existsSync(filePath)) return null;
  try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
  catch { return null; }
}

function getLatestDate() {
  const dir = path.join(REPO_ROOT, 'reports', 'json', 'regional');
  if (!fs.existsSync(dir)) return null;
  const dates = fs.readdirSync(dir)
    .filter(f => fs.statSync(path.join(dir, f)).isDirectory())
    .sort().reverse();
  return dates[0] || null;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 'no-store');

  try {
    const requestedDate = req.query.date;
    const regionFilter  = req.query.region;

    const dateKey = requestedDate || getLatestDate();
    if (!dateKey) {
      return res.status(404).json({ error: 'No regional data found', hint: 'Run regional report generator first.' });
    }

    const basePath  = path.join(REPO_ROOT, 'reports', 'json', 'regional', dateKey);
    const indexData = readJSON(path.join(basePath, 'index.json'));

    const regionKeys = regionFilter && REGION_META[regionFilter]
      ? [regionFilter]
      : Object.keys(REGION_META);

    const regions = [];
    const detail  = {};

    for (const rid of regionKeys) {
      const rd   = readJSON(path.join(basePath, `${rid}.json`));
      const meta = REGION_META[rid];

      const totalRecords = rd?.total_records   ?? indexData?.regions?.[rid]?.total_records   ?? 0;
      const chineseTotal = rd?.chinese_brand_total ?? indexData?.regions?.[rid]?.chinese_brand_total ?? 0;
      const countries    = rd?.countries       ?? indexData?.regions?.[rid]?.countries       ?? [];
      const topProduct   = rd?.product_breakdown
        ? Object.entries(rd.product_breakdown).sort((a,b)=>b[1]-a[1])[0]?.[0] ?? '-' : '-';
      const topBrand     = rd?.brand_breakdown
        ? Object.entries(rd.brand_breakdown).sort((a,b)=>b[1]-a[1])[0]?.[0] ?? '-' : '-';

      const summary = {
        id: rid, name: meta.name, flag: meta.flag, en: meta.en,
        totalRecords, countriesCount: countries.length, countries,
        topProduct, topBrand,
        chineseSignals: chineseTotal,
        lgTotal: rd?.lg_total ?? (totalRecords - chineseTotal),
        periodStart: rd?.period_start ?? indexData?.period_start,
        periodEnd:   rd?.period_end   ?? indexData?.period_end,
      };

      regions.push(summary);
      if (rd) detail[rid] = rd;
    }

    if (regionFilter) {
      return res.status(200).json({
        success: true,
        data: regions[0] ?? null,
        detail: detail[regionFilter] ?? null,
        meta: { dateKey, region: regionFilter },
      });
    }

    return res.status(200).json({
      success: true,
      data: { regions, detail },
      meta: {
        dateKey,
        periodStart: indexData?.period_start,
        periodEnd:   indexData?.period_end,
        totalRecords: indexData?.total_records ?? regions.reduce((s,r) => s + r.totalRecords, 0),
        generatedAt: new Date().toISOString(),
      },
    });

  } catch (error) {
    console.error('Regions local API error:', error);
    return res.status(500).json({ error: 'Failed', message: error.message });
  }
}
