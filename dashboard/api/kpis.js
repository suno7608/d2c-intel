/**
 * GET /api/kpis
 * Returns dashboard KPI metrics from latest weekly stats.
 * Query params:
 *   ?date=YYYY-MM-DD  (optional, defaults to latest)
 */

import {
  fetchJSON,
  getLatestWeeklyDate,
  getReportDates,
  computeKPIs,
} from './_lib/github.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=600');

  try {
    const requestedDate = req.query.date;
    let dateKey = requestedDate;

    if (!dateKey) {
      dateKey = await getLatestWeeklyDate();
      if (!dateKey) {
        return res.status(404).json({ error: 'No weekly stats found' });
      }
    }

    const currentStats = await fetchJSON(`data/weekly_stats/${dateKey}.json`);

    // Try to get previous week for delta calculation
    let previousStats = null;
    try {
      const dates = await getReportDates();
      const idx = dates.indexOf(dateKey);
      if (idx >= 0 && idx < dates.length - 1) {
        previousStats = await fetchJSON(`data/weekly_stats/${dates[idx + 1]}.json`);
      }
    } catch (e) {
      // Previous stats not available — deltas will be 0
    }

    const kpis = computeKPIs(currentStats, previousStats);

    return res.status(200).json({
      success: true,
      data: kpis,
      meta: {
        dateKey,
        generatedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    console.error('KPI API error:', error);
    return res.status(500).json({
      error: 'Failed to fetch KPI data',
      message: error.message,
    });
  }
}
