import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { fetchWeeklyReports, fetchWeeklyReport } from "../api/client";
import { format } from "date-fns";
import { Card, CardBody, CardHeader, Spinner } from "../components/ui";
import { ReportMarkdown } from "../components/ReportMarkdown";

export default function WeeklyReportPage() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data: reports, isLoading } = useQuery({
    queryKey: ["weekly-reports"],
    queryFn: fetchWeeklyReports,
  });
  const { data: report } = useQuery({
    queryKey: ["weekly-report", selectedId],
    queryFn: () => fetchWeeklyReport(selectedId!),
    enabled: selectedId != null,
  });

  useEffect(() => {
    if (reports?.length && selectedId == null) setSelectedId(reports[0].id);
  }, [reports, selectedId]);

  return (
    <div>
      <div className="mb-6">
        <h2 className="font-display text-xl sm:text-2xl font-semibold text-white">Weekly reports</h2>
        <p className="text-[13px] sm:text-sm text-white/70 mt-1">Auto-generated summaries of the top signals per week.</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-6">
        <aside className="sm:w-72 shrink-0">
          <Card>
            <CardHeader className="flex items-center justify-between gap-3">
              <h3 className="text-white font-medium text-sm">Select period</h3>
              {isLoading ? <Spinner /> : null}
            </CardHeader>
            <CardBody>
              <ul className="space-y-1">
                {reports?.map((r) => (
                  <li key={r.id}>
                    <button
                      onClick={() => setSelectedId(r.id)}
                      className={`w-full text-left rounded-xl px-3 py-2 text-sm transition-colors border ${
                        selectedId === r.id
                          ? "bg-white/10 text-white border-white/15"
                          : "text-white/75 hover:bg-white/5 border-transparent"
                      }`}
                    >
                      <div className="font-medium">
                        {format(new Date(r.period_start), "MMM d")} – {format(new Date(r.period_end), "MMM d, yyyy")}
                      </div>
                      <div className="text-xs text-white/55 mt-0.5">Report ID {r.id}</div>
                    </button>
                  </li>
                ))}
              </ul>
              {reports?.length === 0 ? (
                <p className="text-white/60 text-sm">
                  No reports yet. Weekly reports are generated automatically.
                </p>
              ) : null}
            </CardBody>
          </Card>
        </aside>

        <article className="flex-1 min-w-0">
          {!selectedId && (
            <Card>
              <CardBody>
                <p className="text-white/70">Select a report from the list.</p>
              </CardBody>
            </Card>
          )}
          {selectedId && !report && (
            <div className="py-6">
              <Spinner label="Loading report…" />
            </div>
          )}
          {report?.report_markdown && (
            <div className="rounded-3xl border border-white/10 bg-white/4 shadow-[0_10px_40px_rgba(0,0,0,0.35)] p-6 sm:p-8 md:p-10">
              <ReportMarkdown markdown={report.report_markdown} />
            </div>
          )}
          {report && !report.report_markdown && (
            <Card>
              <CardBody>
                <p className="text-white/70">This report has no content.</p>
              </CardBody>
            </Card>
          )}
        </article>
      </div>
    </div>
  );
}
