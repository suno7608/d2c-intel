/**
 * GET /api/search
 * Intelligence search across all collected data.
 * Query params:
 *   ?q=search+terms    (required)
 *   ?product=TV         (optional filter)
 *   ?country=US         (optional filter)
 *   ?brand=LG           (optional filter)
 *   ?pillar=...         (optional filter)
 *   ?date=YYYY-MM-DD    (specific week, default latest)
 *   ?limit=30           (max results)
 */

import {
  fetchJSONL,
  getLatestWeeklyDate,
  getReportDates,
} from './_lib/github.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Cache-Control', 's-maxage=60, stale-while-revalidate=120');

  try {
    const {
      q,
      product,
      country,
      brand,
      pillar,
      date,
      limit = '30',
    } = req.query;

    if (!q) {
      return res.status(400).json({ error: 'Search query (q) is required' });
    }

    const maxResults = Math.min(parseInt(limit) || 30, 100);
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);

    // Determine which dates to search
    let datesToSearch = [];
    if (date) {
      datesToSearch = [date];
    } else {
      const allDates = await getReportDates();
      datesToSearch = allDates.slice(0, 4); // Search last 4 weeks
    }

    let allResults = [];

    for (const dateKey of datesToSearch) {
      try {
        const records = await fetchJSONL(`data/raw/openclaw_${dateKey}.jsonl`);

        for (const r of records) {
          // Apply filters
          if (product && r.product?.toLowerCase() !== product.toLowerCase()) continue;
          if (country && r.country?.toUpperCase() !== country.toUpperCase()) continue;
          if (brand && r.brand?.toLowerCase() !== brand.toLowerCase()) continue;
          if (pillar && !r.pillar?.toLowerCase().includes(pillar.toLowerCase())) continue;

          // Text search
          const text = [r.value, r.quote_original, r.source, r.brand, r.product, r.country]
            .filter(Boolean)
            .join(' ')
            .toLowerCase();

          const matchCount = terms.filter(t => text.includes(t)).length;
          if (matchCount === terms.length) {
            allResults.push({
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
              dateKey,
              relevance: matchCount / terms.length,
            });
          }
        }
      } catch (e) {
        // Skip dates that fail
      }
    }

    // Sort by relevance then confidence
    allResults.sort((a, b) => {
      if (b.relevance !== a.relevance) return b.relevance - a.relevance;
      const confOrder = { high: 2, medium: 1, low: 0 };
      return (confOrder[b.confidence] || 0) - (confOrder[a.confidence] || 0);
    });

    const results = allResults.slice(0, maxResults);

    // Facets
    const facets = {
      products: {},
      countries: {},
      brands: {},
      pillars: {},
    };
    for (const r of allResults) {
      if (r.product) facets.products[r.product] = (facets.products[r.product] || 0) + 1;
      if (r.country) facets.countries[r.country] = (facets.countries[r.country] || 0) + 1;
      if (r.brand) facets.brands[r.brand] = (facets.brands[r.brand] || 0) + 1;
      if (r.pillar) facets.pillars[r.pillar] = (facets.pillars[r.pillar] || 0) + 1;
    }

    return res.status(200).json({
      success: true,
      data: {
        results,
        facets,
        totalMatches: allResults.length,
      },
      meta: {
        query: q,
        filters: { product, country, brand, pillar },
        datesSearched: datesToSearch,
        generatedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    console.error('Search API error:', error);
    return res.status(500).json({
      error: 'Search failed',
      message: error.message,
    });
  }
}
