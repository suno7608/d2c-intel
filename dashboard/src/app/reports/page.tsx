import { getReportDates, getReportMetadata } from "@/lib/data";
import Link from "next/link";

export default function ReportsPage() {
  const dates = getReportDates();

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Weekly Reports</h1>

      {dates.length === 0 ? (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-12 text-center">
          <p className="text-lg font-medium">No reports available</p>
          <p className="mt-2 text-sm text-[var(--muted)]">Reports will appear here after the pipeline runs.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {dates.map((date) => {
            const meta = getReportMetadata(date);
            return (
              <Link
                key={date}
                href={`/reports/${date}`}
                className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-5 hover:border-[var(--accent)] transition-colors"
              >
                <p className="text-lg font-bold">{date}</p>
                {meta && (
                  <>
                    <p className="mt-1 text-sm text-[var(--muted)]">
                      {meta.report_period?.start} ~ {meta.report_period?.end}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {meta.metrics &&
                        Object.entries(meta.metrics)
                          .slice(0, 3)
                          .map(([k, v]) => (
                            <span key={k} className="rounded bg-[var(--accent-light)] px-2 py-0.5 text-xs">
                              {k}: {v}
                            </span>
                          ))}
                    </div>
                    {meta.executive_key_insights && meta.executive_key_insights.length > 0 && (
                      <p className="mt-3 text-xs text-[var(--muted)] line-clamp-2">
                        {meta.executive_key_insights[0].replace(/<[^>]*>/g, "")}
                      </p>
                    )}
                  </>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
