"use client";

import { useState, useMemo } from "react";

interface RawRecord {
  country: string;
  product: string;
  pillar: string;
  brand: string;
  signal_type: string;
  value: string;
  currency: string;
  price_value: string;
  discount: string;
  rating: string;
  source_url: string;
  source: string;
  collected_at: string;
}

const PRODUCTS = ["All", "TV", "Refrigerator", "Washing Machine", "Monitor", "LG gram"];
const PILLARS = ["All", "chinese_brand_threat", "retail_channel_promotions", "competitive_price_positioning", "consumer_sentiment", "market_signal"];
const PILLAR_LABELS: Record<string, string> = {
  chinese_brand_threat: "Chinese Brand Threat",
  retail_channel_promotions: "Retail Promotions",
  competitive_price_positioning: "Price & Positioning",
  consumer_sentiment: "Consumer Sentiment",
  market_signal: "Market Signal",
};

export default function ExplorePage() {
  const [records, setRecords] = useState<RawRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [product, setProduct] = useState("All");
  const [pillar, setPillar] = useState("All");
  const [brand, setBrand] = useState("");
  const [country, setCountry] = useState("");

  async function loadData() {
    setLoading(true);
    try {
      const res = await fetch("/api/records");
      const data = await res.json();
      setRecords(data);
      setLoaded(true);
    } catch {
      setRecords([]);
    }
    setLoading(false);
  }

  const filtered = useMemo(() => {
    return records.filter((r) => {
      if (product !== "All" && r.product !== product) return false;
      if (pillar !== "All" && r.pillar !== pillar) return false;
      if (brand && !r.brand.toLowerCase().includes(brand.toLowerCase())) return false;
      if (country && !r.country.toLowerCase().includes(country.toLowerCase())) return false;
      return true;
    });
  }, [records, product, pillar, brand, country]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Data Explorer</h1>
      <p className="text-sm text-[var(--muted)]">Browse and filter all collected intelligence data.</p>

      {!loaded ? (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-12 text-center">
          <p className="text-lg font-medium mb-4">Load accumulated data to start exploring</p>
          <button
            onClick={loadData}
            disabled={loading}
            className="rounded-md bg-[var(--accent)] px-6 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load Data"}
          </button>
        </div>
      ) : (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <select
              value={product}
              onChange={(e) => setProduct(e.target.value)}
              className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-1.5 text-sm"
            >
              {PRODUCTS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <select
              value={pillar}
              onChange={(e) => setPillar(e.target.value)}
              className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-1.5 text-sm"
            >
              {PILLARS.map((p) => (
                <option key={p} value={p}>{p === "All" ? "All Pillars" : PILLAR_LABELS[p] || p}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Brand..."
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-1.5 text-sm w-32"
            />
            <input
              type="text"
              placeholder="Country..."
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="rounded-md border border-[var(--card-border)] bg-[var(--card)] px-3 py-1.5 text-sm w-32"
            />
            <span className="flex items-center text-xs text-[var(--muted)]">
              {filtered.length} / {records.length} records
            </span>
          </div>

          {/* Results Table */}
          <div className="overflow-x-auto rounded-lg border border-[var(--card-border)]">
            <table className="w-full text-sm">
              <thead className="bg-[var(--card)] text-left">
                <tr>
                  <th className="px-3 py-2 font-medium">Country</th>
                  <th className="px-3 py-2 font-medium">Product</th>
                  <th className="px-3 py-2 font-medium">Brand</th>
                  <th className="px-3 py-2 font-medium">Pillar</th>
                  <th className="px-3 py-2 font-medium">Signal</th>
                  <th className="px-3 py-2 font-medium">Price</th>
                  <th className="px-3 py-2 font-medium max-w-xs">Value</th>
                  <th className="px-3 py-2 font-medium">Source</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 100).map((r, i) => (
                  <tr key={i} className="border-t border-[var(--card-border)] hover:bg-[var(--card)]">
                    <td className="px-3 py-2">{r.country}</td>
                    <td className="px-3 py-2">{r.product}</td>
                    <td className="px-3 py-2 font-medium">{r.brand}</td>
                    <td className="px-3 py-2 text-xs">{PILLAR_LABELS[r.pillar] || r.pillar}</td>
                    <td className="px-3 py-2 text-xs">{r.signal_type}</td>
                    <td className="px-3 py-2 text-xs">{r.price_value ? `${r.currency} ${r.price_value}` : "-"}</td>
                    <td className="px-3 py-2 text-xs max-w-xs truncate">{r.value}</td>
                    <td className="px-3 py-2">
                      {r.source_url ? (
                        <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="text-[var(--accent)] hover:underline text-xs">
                          Link
                        </a>
                      ) : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > 100 && (
              <p className="p-3 text-xs text-[var(--muted)] text-center">
                Showing first 100 of {filtered.length} results
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
