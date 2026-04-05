import { getReportHTML, getReportMetadata, getReportDates } from "@/lib/data";
import Link from "next/link";

export default async function ReportDetailPage({
  params,
}: {
  params: Promise<{ date: string }>;
}) {
  const { date } = await params;
  const meta = getReportMetadata(date);
  const htmlKo = getReportHTML(date, "ko");
  const htmlEn = getReportHTML(date, "en");
  const dates = getReportDates();
  const currentIdx = dates.indexOf(date);
  const prevDate = currentIdx < dates.length - 1 ? dates[currentIdx + 1] : null;
  const nextDate = currentIdx > 0 ? dates[currentIdx - 1] : null;

  if (!htmlKo && !htmlEn) {
    return (
      <div className="space-y-6">
        <Link href="/reports" className="text-sm text-[var(--accent)] hover:underline">
          &larr; Back to Reports
        </Link>
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-12 text-center">
          <p className="text-lg font-medium">Report not found</p>
          <p className="mt-2 text-sm text-[var(--muted)]">No report available for {date}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Link href="/reports" className="text-sm text-[var(--accent)] hover:underline">
          &larr; Back to Reports
        </Link>
        <div className="flex items-center gap-2">
          {prevDate && (
            <Link href={`/reports/${prevDate}`} className="rounded-md border border-[var(--card-border)] px-3 py-1 text-sm hover:bg-[var(--background)]">
              &larr; {prevDate}
            </Link>
          )}
          {nextDate && (
            <Link href={`/reports/${nextDate}`} className="rounded-md border border-[var(--card-border)] px-3 py-1 text-sm hover:bg-[var(--background)]">
              {nextDate} &rarr;
            </Link>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Report: {date}</h1>
        {meta && (
          <p className="text-sm text-[var(--muted)]">
            {meta.report_period?.start} ~ {meta.report_period?.end}
          </p>
        )}
      </div>

      {meta?.executive_key_insights && meta.executive_key_insights.length > 0 && (
        <div className="rounded-lg border border-[var(--card-border)] bg-[var(--card)] p-4">
          <h2 className="text-sm font-semibold mb-2">Key Insights</h2>
          <ul className="space-y-1">
            {meta.executive_key_insights.map((ins, i) => (
              <li key={i} className="text-sm text-[var(--muted)]" dangerouslySetInnerHTML={{ __html: `${i + 1}. ${ins}` }} />
            ))}
          </ul>
        </div>
      )}

      <ReportTabs htmlKo={htmlKo} htmlEn={htmlEn} />
    </div>
  );
}

function ReportTabs({ htmlKo, htmlEn }: { htmlKo: string | null; htmlEn: string | null }) {
  const content = htmlKo || htmlEn || "";
  return (
    <div className="rounded-lg border border-[var(--card-border)] bg-white">
      <iframe
        srcDoc={content}
        className="w-full border-0 rounded-lg"
        style={{ minHeight: "80vh" }}
        title="Weekly Report"
        sandbox="allow-same-origin"
      />
    </div>
  );
}
