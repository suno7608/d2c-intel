import { getWeeklyStatsList, REGIONS, COUNTRY_FLAGS, COUNTRY_NAMES } from "@/lib/data";
import { StatCard } from "@/components/cards";
import { BrandBar, ProductDonut } from "@/components/charts";
import Link from "next/link";

export default async function RegionDetailPage({
  params,
}: {
  params: Promise<{ region: string }>;
}) {
  const { region } = await params;
  const cfg = REGIONS[region];

  if (!cfg) {
    return (
      <div className="space-y-4">
        <Link href="/regions" className="text-sm text-[var(--accent)] hover:underline">&larr; Back to Regions</Link>
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-12 text-center">
          <p className="text-lg font-medium">Region not found</p>
        </div>
      </div>
    );
  }

  const allStats = getWeeklyStatsList();
  const latest = allStats[allStats.length - 1] ?? null;

  const countryRecords = cfg.countries.map((c) => ({
    code: c,
    flag: COUNTRY_FLAGS[c] || "",
    name: COUNTRY_NAMES[c] || c,
    count: latest?.countries[c] ?? 0,
  }));
  const totalRecords = countryRecords.reduce((s, c) => s + c.count, 0);

  // Aggregate brands for this region from raw records would be ideal,
  // but we work with what's available in weekly stats
  const chineseInRegion = latest
    ? cfg.countries.reduce((s, c) => s + (latest.chinese_by_country?.[c] ?? 0), 0)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Link href="/regions" className="text-sm text-[var(--accent)] hover:underline">&larr; Back to Regions</Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold">{cfg.name}</h1>
        <p className="text-sm text-[var(--muted)]">{cfg.nameKo} &middot; {cfg.countries.length} countries</p>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard title="Total Records" value={totalRecords} icon="📊" />
        <StatCard title="Countries" value={cfg.countries.length} icon="🌍" color="info" />
        <StatCard title="Chinese Threat" value={chineseInRegion} icon="⚠️" color="warning" />
        <StatCard
          title="Avg per Country"
          value={cfg.countries.length > 0 ? Math.round(totalRecords / cfg.countries.length) : 0}
          icon="📈"
        />
      </div>

      <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
        <h2 className="text-sm font-semibold mb-3">Countries</h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {countryRecords.map((c) => (
            <div
              key={c.code}
              className="flex items-center justify-between rounded-md border border-[var(--card-border)] px-4 py-3"
            >
              <div className="flex items-center gap-2">
                <span className="text-xl">{c.flag}</span>
                <div>
                  <p className="text-sm font-medium">{c.name}</p>
                  <p className="text-xs text-[var(--muted)]">{c.code}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-lg font-bold">{c.count}</p>
                <p className="text-xs text-[var(--muted)]">records</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {latest && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
          <h2 className="text-sm font-semibold mb-2">Records Distribution</h2>
          <ProductDonut
            data={countryRecords.map((c) => ({ name: c.code, value: c.count }))}
          />
        </div>
      )}
    </div>
  );
}
