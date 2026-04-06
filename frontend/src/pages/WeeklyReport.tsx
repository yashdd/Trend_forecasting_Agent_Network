import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import {
  fetchWeeklyReports,
  fetchWeeklyReport,
  fetchReportSettings,
  putReportSettings,
  generateReportNow,
} from "../api/client";
import { format, subDays } from "date-fns";
import { Badge, Button, Card, CardBody, CardHeader, Spinner, cx } from "../components/ui";
import { ReportMarkdown } from "../components/ReportMarkdown";
import { humanizeToken } from "../utils/format";

const CATEGORY_OPTIONS = [
  { value: "startups", label: "Startups" },
  { value: "open_source_tools", label: "OSS Tools" },
  { value: "research_methods", label: "Research" },
  { value: "ai_models", label: "AI Models" },
  { value: "developer_platforms", label: "Platforms" },
  { value: "security_privacy", label: "Security" },
  { value: "cloud_infra", label: "Cloud/Infra" },
  { value: "robotics_hardware", label: "Robotics/HW" },
  { value: "web3_fintech", label: "Web3/Fintech" },
  { value: "policy_regulation", label: "Policy" },
] as const;

const inputClass =
  "mt-1.5 w-full rounded-xl border border-white/10 bg-black/20 px-3 h-11 text-sm text-white/90 placeholder:text-white/35 focus:outline-none focus:ring-2 focus:ring-cyan-400/25 focus:border-cyan-300/25";

export default function WeeklyReportPage() {
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const { data: reports, isLoading: reportsLoading } = useQuery({
    queryKey: ["weekly-reports"],
    queryFn: fetchWeeklyReports,
  });
  const { data: report, isLoading: reportLoading } = useQuery({
    queryKey: ["weekly-report", selectedId],
    queryFn: () => fetchWeeklyReport(selectedId!),
    enabled: selectedId != null,
  });

  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ["report-settings"],
    queryFn: fetchReportSettings,
  });

  const [lookbackDays, setLookbackDays] = useState(1);
  const [maxTopics, setMaxTopics] = useState(10);
  const [categoryPick, setCategoryPick] = useState<Set<string>>(new Set());
  const [settingsDirty, setSettingsDirty] = useState(false);

  const [rangeStart, setRangeStart] = useState(() => format(subDays(new Date(), 7), "yyyy-MM-dd"));
  const [rangeEnd, setRangeEnd] = useState(() => format(subDays(new Date(), 1), "yyyy-MM-dd"));

  const [savingPrefs, setSavingPrefs] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [prefsMsg, setPrefsMsg] = useState<string | null>(null);
  const [genError, setGenError] = useState<string | null>(null);

  useEffect(() => {
    if (reports?.length && selectedId == null) setSelectedId(reports[0].id);
  }, [reports, selectedId]);

  useEffect(() => {
    if (!settings || settingsDirty) return;
    setLookbackDays(settings.lookback_days);
    setMaxTopics(settings.max_topics);
    if (settings.categories?.length) {
      setCategoryPick(new Set(settings.categories));
    } else {
      setCategoryPick(new Set());
    }
  }, [settings, settingsDirty]);

  const toggleCategory = (value: string) => {
    setSettingsDirty(true);
    setCategoryPick((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  };

  const onSavePreferences = async () => {
    setPrefsMsg(null);
    setSavingPrefs(true);
    try {
      await putReportSettings({
        lookback_days: lookbackDays,
        max_topics: maxTopics,
        categories: categoryPick.size ? Array.from(categoryPick) : null,
      });
      await qc.invalidateQueries({ queryKey: ["report-settings"] });
      setSettingsDirty(false);
      setPrefsMsg("Saved. The next automatic daily report will use these preferences.");
    } catch (e) {
      setPrefsMsg((e as Error).message || "Could not save preferences.");
    } finally {
      setSavingPrefs(false);
    }
  };

  const onGenerate = async () => {
    setGenError(null);
    setGenerating(true);
    try {
      const { id } = await generateReportNow({
        period_start: rangeStart,
        period_end: rangeEnd,
        categories: categoryPick.size ? Array.from(categoryPick) : null,
        max_topics: maxTopics,
      });
      await qc.invalidateQueries({ queryKey: ["weekly-reports"] });
      setSelectedId(id);
      setPrefsMsg(null);
    } catch (e) {
      setGenError((e as Error).message || "Generation failed.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h2 className="font-display text-xl sm:text-2xl font-semibold text-white">Trend reports</h2>
        <p className="text-[13px] sm:text-sm text-white/70 mt-1 max-w-2xl">
          Set preferences for the automatic daily summary, or generate a one-off report for any date range. One scheduled
          report runs per day (typically covering yesterday with your chosen lookback).
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,320px)]">
        <div className="space-y-6 min-w-0">
          <Card>
            <CardHeader>
              <div>
                <p className="text-white font-medium">Preferences (daily + custom runs)</p>
                <p className="text-xs text-white/55 mt-1">
                  Categories and max topics apply to manual “Generate” as well unless you change them here first.
                </p>
              </div>
              {settingsLoading ? <Spinner label="" /> : null}
            </CardHeader>
            <CardBody className="space-y-5">
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="block text-sm text-white/80">
                  Lookback window (days)
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={lookbackDays}
                    onChange={(e) => {
                      setSettingsDirty(true);
                      setLookbackDays(Number(e.target.value) || 1);
                    }}
                    className={inputClass}
                  />
                  <span className="text-xs text-white/45 mt-1 block">
                    For the daily job: end date is yesterday; start = end minus (lookback − 1) days.
                  </span>
                </label>
                <label className="block text-sm text-white/80">
                  Max topics in report
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={maxTopics}
                    onChange={(e) => {
                      setSettingsDirty(true);
                      setMaxTopics(Number(e.target.value) || 10);
                    }}
                    className={inputClass}
                  />
                </label>
              </div>

              <div>
                <p className="text-sm text-white/80 mb-2">Categories</p>
                <p className="text-xs text-white/45 mb-2">Leave none selected to include all categories.</p>
                <div className="flex flex-wrap gap-2">
                  {CATEGORY_OPTIONS.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => toggleCategory(c.value)}
                      className={cx(
                        "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                        categoryPick.has(c.value)
                          ? "border-cyan-400/40 bg-cyan-400/15 text-cyan-100"
                          : "border-white/10 bg-white/5 text-white/70 hover:bg-white/10"
                      )}
                    >
                      {c.label}
                    </button>
                  ))}
                </div>
              </div>

              {prefsMsg ? <p className="text-sm text-emerald-300/90">{prefsMsg}</p> : null}

              <div className="flex flex-wrap gap-3">
                <Button type="button" onClick={() => void onSavePreferences()} disabled={savingPrefs}>
                  {savingPrefs ? "Saving…" : "Save preferences"}
                </Button>
                {settings?.updated_at ? (
                  <span className="text-xs text-white/45 self-center">
                    Last saved {format(new Date(settings.updated_at), "MMM d, yyyy HH:mm")}
                  </span>
                ) : null}
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <p className="text-white font-medium">Custom range</p>
                <p className="text-xs text-white/55 mt-1">Creates an extra report entry (does not replace the daily job).</p>
              </div>
            </CardHeader>
            <CardBody className="space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="block text-sm text-white/80">
                  Start date
                  <input
                    type="date"
                    value={rangeStart}
                    onChange={(e) => setRangeStart(e.target.value)}
                    className={cx(inputClass, "[color-scheme:dark]")}
                  />
                </label>
                <label className="block text-sm text-white/80">
                  End date
                  <input
                    type="date"
                    value={rangeEnd}
                    onChange={(e) => setRangeEnd(e.target.value)}
                    className={cx(inputClass, "[color-scheme:dark]")}
                  />
                </label>
              </div>
              {genError ? <p className="text-sm text-rose-300">{genError}</p> : null}
              <Button type="button" onClick={() => void onGenerate()} disabled={generating}>
                {generating ? "Generating…" : "Generate report for range"}
              </Button>
            </CardBody>
          </Card>

          <div>
            {!selectedId && (
              <Card>
                <CardBody>
                  <p className="text-white/70">Select a report from the list.</p>
                </CardBody>
              </Card>
            )}
            {selectedId && reportLoading && (
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
          </div>
        </div>

        <aside className="lg:sticky lg:top-24 h-fit space-y-4">
          <Card>
            <CardHeader className="flex items-center justify-between gap-3">
              <h3 className="text-white font-medium text-sm">History</h3>
              {reportsLoading ? <Spinner label="" /> : null}
            </CardHeader>
            <CardBody>
              <ul className="space-y-1 max-h-[min(70vh,480px)] overflow-y-auto pr-1">
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
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">
                          {format(new Date(r.period_start), "MMM d")} – {format(new Date(r.period_end), "MMM d, yyyy")}
                        </span>
                        {r.source === "manual" ? (
                          <Badge tone="sky">Custom</Badge>
                        ) : (
                          <Badge tone="slate">Daily</Badge>
                        )}
                      </div>
                      <div className="text-xs text-white/45 mt-0.5">
                        {r.preferences?.categories && Array.isArray(r.preferences.categories) ? (
                          <>
                            {(r.preferences.categories as string[]).slice(0, 3).map(humanizeToken).join(", ")}
                            {(r.preferences.categories as string[]).length > 3 ? "…" : ""}
                          </>
                        ) : (
                          "All categories"
                        )}{" "}
                        · #{r.id}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
              {reports?.length === 0 ? (
                <p className="text-white/60 text-sm">
                  No reports yet. Save preferences for the daily job, or generate a custom range.
                </p>
              ) : null}
            </CardBody>
          </Card>
        </aside>
      </div>
    </div>
  );
}
