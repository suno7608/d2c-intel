"use client";

import { useState } from "react";

interface SearchResult {
  country: string;
  product: string;
  pillar: string;
  brand: string;
  signal_type: string;
  value: string;
  currency: string;
  price_value: string;
  source_url: string;
  source: string;
  collected_at: string;
}

const PILLAR_LABELS: Record<string, string> = {
  chinese_brand_threat: "Chinese Threat",
  retail_channel_promotions: "Retail Promo",
  competitive_price_positioning: "Price Intel",
  consumer_sentiment: "Consumer",
  market_signal: "Market Signal",
};

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query.trim())}`);
      const data = await res.json();
      setResults(data);
      setSearched(true);
    } catch {
      setResults([]);
    }
    setLoading(false);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Search Intelligence</h1>
      <p className="text-sm text-[var(--muted)]">
        Full-text search across all collected data. Search by brand, product, country, or any keyword.
      </p>

      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for brands, products, countries, keywords..."
          className="flex-1 rounded-md border border-[var(--card-border)] bg-[var(--card)] px-4 py-2 text-sm focus:outline-none focus:border-[var(--accent)]"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-[var(--accent)] px-6 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {searched && (
        <p className="text-sm text-[var(--muted)]">
          {results.length === 200 ? "200+ results" : `${results.length} results`} for &ldquo;{query}&rdquo;
        </p>
      )}

      {searched && results.length === 0 && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-8 text-center">
          <p className="text-sm text-[var(--muted)]">No results found. Try different keywords.</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((r, i) => (
            <div key={i} className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="rounded bg-[var(--accent-light)] px-2 py-0.5 text-xs font-medium">
                      {r.country}
                    </span>
                    <span className="rounded bg-[var(--accent-light)] px-2 py-0.5 text-xs">
                      {r.product}
                    </span>
                    <span className="rounded bg-[var(--accent-light)] px-2 py-0.5 text-xs">
                      {PILLAR_LABELS[r.pillar] || r.pillar}
                    </span>
                    {r.brand && r.brand !== "Unknown" && (
                      <span className="text-xs font-medium text-[var(--accent)]">{r.brand}</span>
                    )}
                  </div>
                  <p className="text-sm leading-relaxed">{r.value}</p>
                  <div className="mt-2 flex items-center gap-3 text-xs text-[var(--muted)]">
                    {r.signal_type && <span>{r.signal_type}</span>}
                    {r.price_value && <span>{r.currency} {r.price_value}</span>}
                    {r.collected_at && <span>{r.collected_at.slice(0, 10)}</span>}
                  </div>
                </div>
                {r.source_url && (
                  <a
                    href={r.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 text-xs text-[var(--accent)] hover:underline"
                  >
                    Source
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
