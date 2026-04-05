const BASE = "/api/v1";

export const LAST_PIPELINE_TRIGGERED_AT_KEY = "trend_analyzer:last_pipeline_triggered_at";

/** Max signal (trend_insight) id the user has treated as seen — for in-app “new trends” banner. */
export const LAST_SEEN_SIGNAL_ID_KEY = "trend_analyzer:last_seen_signal_id";

export type SourceRef = { name: string; url: string | null; title: string | null };

export type SignalsMeta = {
  newest_insight_id: number;
  newer_count: number;
};

export type SignalFeedItem = {
  id: number;
  topic_id: number;
  topic_label: string | null;
  category?: string | null;
  signal_score: number | null;
  cross_source_strength: number | null;
  novelty_score: number | null;
  predicted_impact: string | null;
  summary: string | null;
  sources: SourceRef[];
  first_detected_at: string | null;
  updated_at: string | null;
};

export type TopicListItem = {
  id: number;
  label: string | null;
  category?: string | null;
  keywords: unknown;
  signal_score: number | null;
  cross_source_strength: number | null;
  mention_count: number | null;
  first_seen_at: string | null;
};

export type TopicDetail = {
  id: number;
  label: string | null;
  category?: string | null;
  keywords: unknown;
  first_seen_at: string | null;
  updated_at: string | null;
  daily_metrics: { date: string; mention_count: number; signal_score: number | null; growth_rate: number | null }[];
  trend_insight: {
    id?: number;
    summary: string | null;
    why_it_matters: string | null;
    industry_impact: string | null;
    representative_sources: unknown;
  } | null;
};

export type TrendCommentOut = {
  id: number;
  trend_insight_id: number;
  body: string;
  author_label: string;
  created_at: string;
};

export type TrendCommentsResponse = {
  viewer_label: string;
  has_more: boolean;
  next_before_id: number | null;
  comments: TrendCommentOut[];
};

export type MomentumPoint = {
  date: string;
  mention_count: number;
  signal_score: number | null;
  growth_rate: number | null;
};

export type DiscussionItem = {
  id: number;
  source: string;
  url: string | null;
  title: string | null;
  body: string | null;
  author: string | null;
  created_at: string | null;
};

export type WeeklyReportListItem = {
  id: number;
  period_start: string;
  period_end: string;
  created_at: string;
  source?: string;
  preferences?: Record<string, unknown> | null;
};

export type WeeklyReportDetail = {
  id: number;
  period_start: string;
  period_end: string;
  top_signals: unknown[];
  report_markdown: string | null;
  created_at: string;
  source?: string;
  preferences?: Record<string, unknown> | null;
};

export type ReportSettingsOut = {
  lookback_days: number;
  max_topics: number;
  categories: string[] | null;
  updated_at: string;
};

/** Lightweight — use for polling instead of fetchSignals(limit: 80). */
export async function fetchSignalsMeta(afterId?: number | null): Promise<SignalsMeta> {
  const sp = new URLSearchParams();
  if (afterId != null && afterId > 0) sp.set("after_id", String(afterId));
  const r = await fetch(`${BASE}/signals/meta?${sp}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchSignals(params?: {
  limit?: number;
  min_score?: number;
  since?: string;
  category?: string;
}): Promise<SignalFeedItem[]> {
  const sp = new URLSearchParams();
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.min_score != null) sp.set("min_score", String(params.min_score));
  if (params?.since) sp.set("since", params.since);
  if (params?.category) sp.set("category", params.category);
  const r = await fetch(`${BASE}/signals?${sp}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchSignal(id: number): Promise<SignalFeedItem> {
  const r = await fetch(`${BASE}/signals/${id}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchTopics(params?: {
  days?: number;
  sort?: string;
  limit?: number;
  category?: string;
}): Promise<TopicListItem[]> {
  const sp = new URLSearchParams();
  if (params?.days) sp.set("days", String(params.days));
  if (params?.sort) sp.set("sort", params.sort);
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.category) sp.set("category", params.category);
  const r = await fetch(`${BASE}/topics?${sp}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchTopic(topicId: number): Promise<TopicDetail> {
  const r = await fetch(`${BASE}/topics/${topicId}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchTopicDiscussions(topicId: number, limit = 50): Promise<DiscussionItem[]> {
  const r = await fetch(`${BASE}/topics/${topicId}/discussions?limit=${limit}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchSignalComments(
  signalId: number,
  params?: { limit?: number; before_id?: number | null }
): Promise<TrendCommentsResponse> {
  const sp = new URLSearchParams();
  if (params?.limit) sp.set("limit", String(params.limit));
  if (params?.before_id) sp.set("before_id", String(params.before_id));
  const r = await fetch(`${BASE}/signals/${signalId}/comments?${sp}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function postSignalComment(signalId: number, body: { body: string }): Promise<TrendCommentOut> {
  const r = await fetch(`${BASE}/signals/${signalId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = r.statusText || `HTTP ${r.status}`;
    try {
      const err = (await r.json()) as { detail?: unknown };
      const d = err.detail;
      if (typeof d === "string") msg = d;
      else if (Array.isArray(d) && d[0] && typeof (d[0] as { msg?: string }).msg === "string")
        msg = (d[0] as { msg: string }).msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return r.json();
}

export async function fetchMomentum(
  topicId: number,
  fromDate?: string,
  toDate?: string
): Promise<MomentumPoint[]> {
  const sp = new URLSearchParams({ topic_id: String(topicId) });
  if (fromDate) sp.set("from", fromDate);
  if (toDate) sp.set("to", toDate);
  const r = await fetch(`${BASE}/metrics/momentum?${sp}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function triggerPipeline(): Promise<{ status: string; message: string }> {
  const r = await fetch(`${BASE}/admin/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!r.ok) throw new Error(r.statusText);
  try {
    localStorage.setItem(LAST_PIPELINE_TRIGGERED_AT_KEY, new Date().toISOString());
  } catch {
    // ignore (private mode / disabled storage)
  }
  return r.json();
}

export async function pingApi(): Promise<boolean> {
  try {
    const r = await fetch(`${BASE}/signals/meta`, { method: "GET" });
    return r.ok;
  } catch {
    return false;
  }
}

export type ExplainEvidenceItem = {
  source: string;
  source_family: string;
  url: string | null;
  title: string | null;
  excerpt: string | null;
  raw_post_id: number | null;
};

export type ExplainabilityResponse = {
  topic_id: number;
  topic_label: string | null;
  category: string | null;
  today: string | null;
  mention_count_today: number | null;
  mention_count_yesterday: number | null;
  growth_rate: number | null;
  acceleration: number | null;
  signal_score: number | null;
  cross_source_strength: number | null;
  source_families: string[];
  top_phrases: string[];
  evidence: ExplainEvidenceItem[];
};

export async function fetchExplainability(topicId: number): Promise<ExplainabilityResponse> {
  const r = await fetch(`${BASE}/explain/topic/${topicId}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export type AlertRuleIn = {
  name: string;
  enabled?: boolean;
  category?: string | null;
  /** All terms must appear in topic title or insight text (case-insensitive). */
  keywords?: string[] | null;
  min_signal_score?: number | null;
  min_cross_source_strength?: number | null;
  /** Omit or leave empty for in-app notifications only */
  webhook_url?: string | null;
  max_events_per_day?: number;
};

export type AlertRuleOut = {
  id: number;
  name: string;
  enabled: boolean;
  category?: string | null;
  keywords?: string[] | null;
  min_signal_score?: number | null;
  min_cross_source_strength?: number | null;
  webhook_url: string | null;
  max_events_per_day: number;
  created_at: string;
};

export const LAST_SEEN_ALERT_EVENT_ID_KEY = "tfa_last_seen_alert_event_id";

export type AlertEventOut = {
  id: number;
  rule_id: number | null;
  topic_id: number;
  trend_insight_id: number | null;
  sent_at: string;
  status: string;
  error_message: string | null;
  rule_name?: string | null;
  topic_label?: string | null;
};

export async function fetchAlertRules(): Promise<AlertRuleOut[]> {
  const r = await fetch(`${BASE}/alerts/rules`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function createAlertRule(body: AlertRuleIn): Promise<AlertRuleOut> {
  const r = await fetch(`${BASE}/alerts/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function updateAlertRule(id: number, body: Partial<AlertRuleIn>): Promise<AlertRuleOut> {
  const r = await fetch(`${BASE}/alerts/rules/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function deleteAlertRule(id: number): Promise<void> {
  const r = await fetch(`${BASE}/alerts/rules/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error(r.statusText);
}

export async function fetchAlertEvents(limit = 50): Promise<AlertEventOut[]> {
  const r = await fetch(`${BASE}/alerts/events?limit=${limit}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchLatestRun(): Promise<any> {
  const r = await fetch(`${BASE}/runs/latest`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function searchAll(q: string): Promise<any> {
  const r = await fetch(`${BASE}/search?q=${encodeURIComponent(q)}&limit=20`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchWeeklyReports(): Promise<WeeklyReportListItem[]> {
  const r = await fetch(`${BASE}/reports/weekly`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchWeeklyReport(id: number): Promise<WeeklyReportDetail> {
  const r = await fetch(`${BASE}/reports/weekly/${id}`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function fetchReportSettings(): Promise<ReportSettingsOut> {
  const r = await fetch(`${BASE}/reports/settings`);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function putReportSettings(body: {
  lookback_days: number;
  max_topics: number;
  categories: string[] | null;
}): Promise<ReportSettingsOut> {
  const r = await fetch(`${BASE}/reports/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export async function generateReportNow(body: {
  period_start: string;
  period_end: string;
  categories?: string[] | null;
  max_topics?: number;
}): Promise<{ id: number }> {
  const r = await fetch(`${BASE}/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = r.statusText;
    try {
      const j = (await r.json()) as { detail?: string | unknown };
      if (typeof j.detail === "string") msg = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return r.json();
}
