/**
 * GET /api/regions
 * Returns regional pulse summary from pre-generated JSON files.
 * Falls back gracefully if JSONL raw data is unavailable.
 *
 * Query params:
 *   ?date=YYYY-MM-DD  (optional, defaults to latest)
 *   ?region=nam|eur|latam|asia|mea  (optional, single region)
 */

import { fetchJSON, listFiles } from './_lib/github.js';

const REGION_META = {
  nam:   { id: 'nam',   name: '북미',         flag: '🌎', en: 'North America' },
  eur:   { id: 'eur',   name: '유럽',         flag: '🌍', en: 'Europe' },
  latam: { id: 'latam', name: '중남미',       flag: '🌎', en: 'Latin America' },
  asia:  { id: 'asia',  name: '아시아',       flag: '🌏', en: 'Asia Pacific' },
  mea:   { id: 'mea',   name: '중동·아프리카', flag: '🌍', en: 'Middle East & Africa' },
};

async function getLatestRegionalDate() {
  try {
    const files = await listFiles('reports/json/regional');
    const dates = files
      .filter(f => f.type === 'dir')
      .map(f => f.name)
      .sort()
      .reverse();
    return dates[0] || null;
  } catch (e) {
    return null;
  }
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');

  try {
    const requestedDate = req.query.date;
    const regionFilter  = req.query.region;

    const dateKey = requestedDate || await getLatestRegionalDate();
    if (!dateKey) {
      return res.status(404).json({ error: 'No regional data found', hint: 'Generate regional JSON files first.' });
    }

    // Load index for period metadata
    let indexData = null;
    try {
      indexData = await fetchJSON(`reports/json/regional/${dateKey}/index.json`);
    } catch (e) { /* optional */ }

    const regionKeys = regionFilter && REGION_META[regionFilter]
      ? [regionFilter]
      : Object.keys(REGION_META);

    // Build per-region summaries from pre-generated JSON
    const regions = [];
    const detail  = {};

    for (const rid of regionKeys) {
      let rd = null;
      try {
        rd = await fetchJSON(`reports/json/regional/${dateKey}/${rid}.json`);
      } catch (e) { /* region file not found */ }

      const meta = REGION_META[rid];
      const totalRecords   = rd?.total_records   ?? indexData?.regions?.[rid]?.total_records   ?? 0;
      const chineseTotal   = rd?.chinese_brand_total ?? indexData?.regions?.[rid]?.chinese_brand_total ?? 0;
      const countries      = rd?.countries       ?? indexData?.regions?.[rid]?.countries       ?? [];
      const topProduct     = rd?.product_breakdown
        ? Object.entries(rd.product_breakdown).sort((a,b) => b[1]-a[1])[0]?.[0] ?? '-'
        : '-';
      const topBrand       = rd?.brand_breakdown
        ? Object.entries(rd.brand_breakdown).sort((a,b) => b[1]-a[1])[0]?.[0] ?? '-'
        : '-';

      const summary = {
        id: rid,
        name: meta.name,
        flag: meta.flag,
        en: meta.en,
        totalRecords,
        countriesCount: countries.length,
        countries,
        topProduct,
        topBrand,
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
    console.error('Regions API error:', error);
    return res.status(500).json({
      error: 'Failed to fetch regional data',
      message: error.message,
    });
  }
}
