/**
 * GET /api/regions
 * Returns regional breakdown aggregated from raw JSONL data.
 * Query params:
 *   ?date=YYYY-MM-DD  (optional, defaults to latest)
 *   ?region=nam|eur|latam|asia|mea  (optional, filter single region)
 */

import {
  fetchJSONL,
  fetchJSON,
  getLatestWeeklyDate,
  aggregateByRegion,
} from './_lib/github.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');

  try {
    const requestedDate = req.query.date;
    const regionFilter = req.query.region;

    let dateKey = requestedDate;
    if (!dateKey) {
      dateKey = await getLatestWeeklyDate();
      if (!dateKey) {
        return res.status(404).json({ error: 'No data found' });
      }
    }

    // Fetch raw JSONL for full record detail
    const records = await fetchJSONL(`data/raw/openclaw_${dateKey}.jsonl`);
    const regions = aggregateByRegion(records);

    // Also get weekly stats for supplementary metrics
    let weeklyStats = null;
    try {
      weeklyStats = await fetchJSON(`data/weekly_stats/${dateKey}.json`);
    } catch (e) { /* optional */ }

    if (regionFilter) {
      const region = regions[regionFilter];
      if (!region) {
        return res.status(404).json({ error: `Region '${regionFilter}' not found` });
      }
      return res.status(200).json({
        success: true,
        data: region,
        meta: { dateKey, region: regionFilter },
      });
    }

    // Build summary for each region
    const summary = Object.values(regions).map(r => ({
      id: r.id,
      name: r.name,
      totalRecords: r.totalRecords,
      countriesCount: Object.keys(r.countries).length,
      topProduct: Object.entries(r.products).sort((a, b) => b[1] - a[1])[0]?.[0] || '-',
      topBrand: Object.entries(r.brands).sort((a, b) => b[1] - a[1])[0]?.[0] || '-',
      chineseSignals: Object.entries(r.brands)
        .filter(([b]) => ['TCL', 'Hisense', 'Haier', 'Midea'].includes(b))
        .reduce((sum, [, v]) => sum + v, 0),
    }));

    return res.status(200).json({
      success: true,
      data: {
        regions: summary,
        detail: regions,
      },
      meta: {
        dateKey,
        totalRecords: records.length,
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
