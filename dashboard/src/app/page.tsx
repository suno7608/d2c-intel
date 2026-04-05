import { getWeeklyStatsList, getReportDates, getReportMetadata, getLatestPriceAlerts, REGIONS, getCountryRegion } from "@/lib/data";
import { StatCard, PriceAlertCard, InsightCard } from "@/components/cards";
import { ProductDonut, BrandBar, WeeklyTrend, RegionBar, PillarChart } from "@/components/charts";
import Link from "next/link";

export default function DashboardPage() {
  const allStats = getWeeklyStatsList();
  const dates = getReportDates();
  const latestDate = dates[0] ?? null;
  const meta = latestDate ? getReportMetadata(latestDate) : null;
  const alerts = getLatestPriceAlerts().slice(0, 5);

  const latest = allStats[allStats.length - 1] ?? null;
  const prev = allStats.length >= 2 ? allStats[allStats.length - 2] : null;

  // Weekly trend data
  const trendData = allStats.slice(-8).map((s) => ({
    week: s.date.slice(5),
    total: s.total_records,
    chinese: s.chinese_brand_total,
    negative: s.consumer_negative_count,
  }));

  // Product distribution
  const productData = latest
    ? Object.entries(latest.products).map(([name, value]) => ({ name, value }))
    : [];

  // Brand distribution (top 8)
  const brandData = latest
    ? Object.entries(latest.brands)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([name, value]) => ({ name, value }))
    : [];

  // Pillar distribution
  const pillarData = latest
    ? Object.entries(latest.pillars).map(([name, value]) => ({ name, value }))
    : [];

  // Region aggregation
  const regionData = Object.entries(REGIONS).map(([key, cfg]) => {
    const records = latest
      ? cfg.countries.reduce((sum, c) => sum + (latest.countries[c] ?? 0), 0)
      : 0;
    return { name: cfg.name, records, countries: cfg.countries.length };
  });

  const noData = !latest;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Executive Dashboard</h1>
          {latestDate && (
            <p className="text-sm text-[var(--muted)]">Latest: Week of {latestDate}</p>
          )}
        </div>
        {latestDate && (
          <Link
            href={`/reports/${latestDate}`}
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            View Full Report
          </Link>
        )}
      </div>

      {noData ? (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-12 text-center">
          <p className="text-lg font-medium">No data available yet</p>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Run the D2C pipeline to generate weekly intelligence data.
          </p>
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard
              title="Total Signals"
              value={latest.total_records}
              icon="📊"
              prev={prev?.total_records}
              current={latest.total_records}
            />
            <StatCard
              title="Chinese Brand Threat"
              value={latest.chinese_brand_total}
              icon="⚠️"
              color="warning"
              prev={prev?.chinese_brand_total}
              current={latest.chinese_brand_total}
            />
            <StatCard
              title="Consumer Negative"
              value={latest.consumer_negative_count}
              icon="👎"
              color="danger"
              prev={prev?.consumer_negative_count}
              current={latest.consumer_negative_count}
            />
            <StatCard
              title="Countries"
              value={latest.countries_count}
              subtitle={`${Object.keys(latest.countries).length} active`}
              icon="🌍"
              color="info"
            />
          </div>

          {/* Executive Insights */}
          {meta?.executive_key_insights && meta.executive_key_insights.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-3">Executive Key Insights</h2>
              <div className="grid gap-3 md:grid-cols-2">
                {meta.executive_key_insights.slice(0, 4).map((insight, i) => (
                  <InsightCard key={i} insight={insight} index={i} />
                ))}
              </div>
            </div>
          )}

          {/* Charts Row 1 */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <h3 className="text-sm font-semibold mb-2">Weekly Trend</h3>
              <WeeklyTrend data={trendData} />
            </div>
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <h3 className="text-sm font-semibold mb-2">Product Distribution</h3>
              <ProductDonut data={productData} />
            </div>
          </div>

          {/* Charts Row 2 */}
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <h3 className="text-sm font-semibold mb-2">Top Brands</h3>
              <BrandBar data={brandData} />
            </div>
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <h3 className="text-sm font-semibold mb-2">Analysis Pillars</h3>
              <PillarChart data={pillarData} />
            </div>
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <h3 className="text-sm font-semibold mb-2">Region Overview</h3>
              <RegionBar data={regionData} />
            </div>
          </div>

          {/* Price Alerts & Region Links */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">Price Alerts</h3>
                {alerts.length > 0 && (
                  <span className="text-xs text-[var(--muted)]">{alerts.length} recent</span>
                )}
              </div>
              {alerts.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No price alerts available</p>
              ) : (
                alerts.map((a, i) => (
                  <PriceAlertCard
                    key={i}
                    brand={a.brand}
                    model={a.model}
                    country={a.country}
                    changePct={a.change_pct}
                    direction={a.direction}
                    currency={a.currency}
                    prevPrice={a.prev_price}
                    newPrice={a.new_price}
                  />
                ))
              )}
            </div>
            <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
              <h3 className="text-sm font-semibold mb-3">Regions</h3>
              <div className="grid grid-cols-1 gap-2">
                {Object.entries(REGIONS).map(([key, cfg]) => {
                  const count = cfg.countries.reduce(
                    (s, c) => s + (latest.countries[c] ?? 0),
                    0
                  );
                  return (
                    <Link
                      key={key}
                      href={`/regions/${key}`}
                      className="flex items-center justify-between rounded-md border border-[var(--card-border)] px-3 py-2 hover:bg-[var(--background)] transition-colors"
                    >
                      <span className="text-sm font-medium">{cfg.name}</span>
                      <span className="text-xs text-[var(--muted)]">
                        {count} records / {cfg.countries.length} countries
                      </span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
