/**
 * GET /api/regional-reports
 * Returns regional report data (structured JSON + markdown).
 *
 * Query params:
 *   ?list=true            — list available regional report dates
 *   ?date=YYYY-MM-DD      — specific date (default: latest)
 *   ?region=nam|eur|latam|asia|mea  — specific region
 *   ?format=json|md|full  — response format (default: full = json + md)
 */

import {
  fetchRawFile,
  fetchJSON,
  listFiles,
} from './_lib/github.js';

const REGIONS = ['nam', 'eur', 'latam', 'asia', 'mea'];
const REGION_NAMES = {
  nam: { ko: '북미', en: 'North America' },
  eur: { ko: '유럽', en: 'Europe' },
  latam: { ko: '중남미', en: 'Latin America' },
  asia: { ko: '아시아 태평양', en: 'Asia Pacific' },
  mea: { ko: '중동·아프리카', en: 'Middle East & Africa' },
};

async function getAvailableDates() {
  try {
    const files = await listFiles('reports/json/regional');
    return files
      .filter(f => f.type === 'dir')
      .map(f => f.name)
      .sort()
      .reverse();
  } catch (e) {
    return [];
  }
}

async function getLatestDate() {
  const dates = await getAvailableDates();
  return dates[0] || null;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');

  try {
    const { list, date, region, format = 'full' } = req.query;

    // ── List mode: return available dates & regions ──
    if (list === 'true') {
      const dates = await getAvailableDates();
      const result = [];

      for (const d of dates.slice(0, 12)) {
        try {
          const index = await fetchJSON(`reports/json/regional/${d}/index.json`);
          result.push({
            date: d,
            period_start: index.period_start,
            period_end: index.period_end,
            regions: Object.keys(index.regions || {}).map(rid => ({
              id: rid,
              ...REGION_NAMES[rid],
              total_records: index.regions[rid]?.total_records || 0,
              chinese_brand_total: index.regions[rid]?.chinese_brand_total || 0,
              countries: index.regions[rid]?.countries || [],
            })),
          });
        } catch (e) {
          result.push({ date: d, regions: [] });
        }
      }

      return res.status(200).json({ success: true, data: { dates: result } });
    }

    // ── Resolve date ──
    const dateKey = date || await getLatestDate();
    if (!dateKey) {
      return res.status(404).json({
        error: 'No regional reports found',
        hint: 'Run the regional report generator first',
      });
    }

    // ── Single region or all regions ──
    const regionsToFetch = region && REGIONS.includes(region)
      ? [region]
      : REGIONS;

    const result = {
      date: dateKey,
      regions: {},
    };

    // Fetch index for period info
    try {
      const index = await fetchJSON(`reports/json/regional/${dateKey}/index.json`);
      result.period_start = index.period_start;
      result.period_end = index.period_end;
    } catch (e) { /* index not available */ }

    for (const rid of regionsToFetch) {
      const entry = { id: rid, ...REGION_NAMES[rid] };

      // Fetch structured JSON
      if (format === 'json' || format === 'full') {
        try {
          entry.data = await fetchJSON(`reports/json/regional/${dateKey}/${rid}.json`);
        } catch (e) {
          entry.data = null;
        }
      }

      // Fetch markdown report
      if (format === 'md' || format === 'full') {
        try {
          const md = await fetchRawFile(`reports/md/regional/${dateKey}/${rid}.md`);
          // Strip YAML frontmatter
          const stripped = md.replace(/^---[\s\S]*?---\s*/, '');
          entry.markdown = stripped;
        } catch (e) {
          entry.markdown = null;
        }
      }

      result.regions[rid] = entry;
    }

    return res.status(200).json({ success: true, data: result });

  } catch (error) {
    console.error('Regional Reports API error:', error);
    return res.status(500).json({
      error: 'Failed to fetch regional reports',
      message: error.message,
    });
  }
}
