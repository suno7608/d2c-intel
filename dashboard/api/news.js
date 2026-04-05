/**
 * GET /api/news
 * Returns daily news clippings from Brave Search.
 * Query params:
 *   ?date=YYYY-MM-DD  (specific date)
 *   ?days=7            (last N days, default 7)
 *   ?product=TV        (filter by product)
 *   ?country=US        (filter by country)
 *   ?q=search+term     (search within news)
 *   ?limit=50          (max results, default 50)
 */

import {
  fetchJSONL,
  listFiles,
} from './_lib/github.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate=120');

  try {
    const {
      date: specificDate,
      days = '7',
      product,
      country,
      q: searchQuery,
      limit = '50',
    } = req.query;

    const maxResults = Math.min(parseInt(limit) || 50, 200);
    let allRecords = [];

    if (specificDate) {
      // Fetch specific date
      try {
        const records = await fetchJSONL(`data/daily_news/${specificDate}.jsonl`);
        allRecords = records;
      } catch (e) {
        // Try raw data as fallback
        try {
          const records = await fetchJSONL(`data/raw/openclaw_${specificDate}.jsonl`);
          allRecords = records;
        } catch (e2) {
          return res.status(404).json({ error: `No news data for ${specificDate}` });
        }
      }
    } else {
      // Fetch last N days
      const numDays = Math.min(parseInt(days) || 7, 30);

      // Try daily_news first, fallback to raw data
      let files = [];
      try {
        files = await listFiles('data/daily_news');
      } catch (e) {
        // daily_news doesn't exist yet, use raw data
        try {
          files = await listFiles('data/raw');
        } catch (e2) {
          return res.status(404).json({ error: 'No news data available' });
        }
      }

      const dateFiles = files
        .filter(f => f.name.endsWith('.jsonl'))
        .map(f => ({
          name: f.name,
          date: f.name.replace('openclaw_', '').replace('.jsonl', ''),
        }))
        .sort((a, b) => b.date.localeCompare(a.date))
        .slice(0, numDays);

      for (const df of dateFiles) {
        try {
          const dirPath = files[0]?.path?.includes('daily_news') ? 'data/daily_news' : 'data/raw';
          const records = await fetchJSONL(`${dirPath}/${df.name}`);
          allRecords.push(...records.map(r => ({ ...r, _dateKey: df.date })));
        } catch (e) {
          // Skip files that can't be read
        }
      }
    }

    // Apply filters
    let filtered = allRecords;

    if (product) {
      filtered = filtered.filter(r =>
        r.product?.toLowerCase() === product.toLowerCase()
      );
    }

    if (country) {
      filtered = filtered.filter(r =>
        r.country?.toUpperCase() === country.toUpperCase()
      );
    }

    if (searchQuery) {
      const terms = searchQuery.toLowerCase().split(/\s+/);
      filtered = filtered.filter(r => {
        const text = [r.value, r.quote_original, r.source, r.brand, r.product]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return terms.every(t => text.includes(t));
      });
    }

    // Sort by collected_at descending, limit results
    filtered.sort((a, b) =>
      (b.collected_at || '').localeCompare(a.collected_at || '')
    );
    const results = filtered.slice(0, maxResults);

    // Build category counts
    const categories = {};
    const countryCounts = {};
    for (const r of filtered) {
      if (r.product) categories[r.product] = (categories[r.product] || 0) + 1;
      if (r.country) countryCounts[r.country] = (countryCounts[r.country] || 0) + 1;
    }

    return res.status(200).json({
      success: true,
      data: {
        articles: results.map(r => ({
          title: r.value,
          snippet: r.quote_original || '',
          source: r.source,
          url: r.source_url,
          country: r.country,
          product: r.product,
          brand: r.brand,
          pillar: r.pillar,
          confidence: r.confidence,
          collectedAt: r.collected_at,
          dateKey: r._dateKey || r.collected_at?.slice(0, 10),
        })),
        totalFiltered: filtered.length,
        categories,
        countryCounts,
      },
      meta: {
        totalRecords: allRecords.length,
        returnedRecords: results.length,
        filters: { product, country, q: searchQuery },
        generatedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    console.error('News API error:', error);
    return res.status(500).json({
      error: 'Failed to fetch news data',
      message: error.message,
    });
  }
}
