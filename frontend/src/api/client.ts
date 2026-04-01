const BASE = "/api/v1";

export const LAST_PIPELINE_TRIGGERED_AT_KEY = "trend_analyzer:last_pipeline_triggered_at";

export type SourceRef = { name: string; url: string | null; title: string | null };

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
    summary: string | null;
    why_it_matters: string | null;
    industry_impact: string | null;
    representative_sources: unknown;
  } | null;
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
};

export type WeeklyReportDetail = {
  id: number;
  period_start: string;
  period_end: string;
  top_signals: unknown[];
  report_markdown: string | null;
  created_at: string;
};

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
    const r = await fetch(`${BASE}/signals?limit=1`, { method: "GET" });
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
  min_signal_score?: number | null;
  min_cross_source_strength?: number | null;
  webhook_url: string;
  max_events_per_day?: number;
};

export type AlertRuleOut = {
  id: number;
  name: string;
  enabled: boolean;
  category?: string | null;
  min_signal_score?: number | null;
  min_cross_source_strength?: number | null;
  webhook_url: string;
  max_events_per_day: number;
  created_at: string;
};

export type AlertEventOut = {
  id: number;
  rule_id: number;
  topic_id: number;
  trend_insight_id: number | null;
  sent_at: string;
  status: string;
  error_message: string | null;
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
