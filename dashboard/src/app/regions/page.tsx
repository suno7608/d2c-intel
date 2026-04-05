import { getWeeklyStatsList, REGIONS, COUNTRY_FLAGS, COUNTRY_NAMES } from "@/lib/data";
import { RegionBar } from "@/components/charts";
import Link from "next/link";

export default function RegionsPage() {
  const allStats = getWeeklyStatsList();
  const latest = allStats[allStats.length - 1] ?? null;

  const regionData = Object.entries(REGIONS).map(([key, cfg]) => {
    const records = latest
      ? cfg.countries.reduce((s, c) => s + (latest.countries[c] ?? 0), 0)
      : 0;
    return { key, ...cfg, records };
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Regional Overview</h1>
      {latest && (
        <p className="text-sm text-[var(--muted)]">Data from week of {latest.date}</p>
      )}

      {!latest ? (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-12 text-center">
          <p className="text-lg font-medium">No data available</p>
        </div>
      ) : (
        <>
          <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
            <h2 className="text-sm font-semibold mb-2">Records by Region</h2>
            <RegionBar
              data={regionData.map((r) => ({
                name: r.name,
                records: r.records,
                countries: r.countries.length,
              }))}
            />
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {regionData.map((r) => (
              <Link
                key={r.key}
                href={`/regions/${r.key}`}
                className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-5 hover:border-[var(--accent)] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold">{r.name}</h3>
                  <span className="text-xs text-[var(--muted)]">{r.nameKo}</span>
                </div>
                <p className="mt-1 text-2xl font-bold text-[var(--accent)]">{r.records}</p>
                <p className="text-xs text-[var(--muted)]">records</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {r.countries.map((c) => (
                    <span key={c} className="text-sm">
                      {COUNTRY_FLAGS[c]} {c}{" "}
                      <span className="text-xs text-[var(--muted)]">({latest.countries[c] ?? 0})</span>
                    </span>
                  ))}
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
