/**
 * GET /api/reports
 * Returns list of available reports and their content.
 * Query params:
 *   ?date=YYYY-MM-DD  (get specific report)
 *   ?list=true        (list all available reports)
 */

import {
  fetchRawFile,
  getReportDates,
  listFiles,
} from './_lib/github.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate=1200');

  try {
    const { date, list } = req.query;

    if (list === 'true' || !date) {
      // Return list of available reports
      const dates = await getReportDates();

      // Try to get report metadata
      let manifest = null;
      try {
        const manifestText = await fetchRawFile('reports/html/manifest.json');
        manifest = JSON.parse(manifestText);
      } catch (e) { /* manifest not available */ }

      return res.status(200).json({
        success: true,
        data: {
          reports: dates.map(d => ({
            date: d,
            htmlUrl: `https://suno7608.github.io/d2c-intel/reports/html/${d}/index.html`,
            pdfUrl: `https://suno7608.github.io/d2c-intel/reports/html/pdf/LG_Global_D2C_Weekly_Intelligence_${d}_R2_16country.pdf`,
          })),
          manifest,
        },
      });
    }

    // Fetch specific report content (markdown)
    const mdPattern = `reports/md/LG_Global_D2C_Weekly_Intelligence_${date}_R2_16country.md`;
    let content = '';
    try {
      content = await fetchRawFile(mdPattern);
    } catch (e) {
      // Try alternative patterns
      try {
        const files = await listFiles('reports/md');
        const match = files.find(f => f.name.includes(date));
        if (match) {
          content = await fetchRawFile(`reports/md/${match.name}`);
        }
      } catch (e2) {
        return res.status(404).json({ error: `Report not found for ${date}` });
      }
    }

    return res.status(200).json({
      success: true,
      data: {
        date,
        content,
        htmlUrl: `https://suno7608.github.io/d2c-intel/reports/html/${date}/index.html`,
      },
    });
  } catch (error) {
    console.error('Reports API error:', error);
    return res.status(500).json({
      error: 'Failed to fetch reports',
      message: error.message,
    });
  }
}
