import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchTopic, fetchTopicDiscussions, fetchMomentum } from "../api/client";
import { Badge, Card, CardBody, CardHeader, Spinner } from "../components/ui";
import { displayInsightText, humanizeToken, humanizeTopicLabel, isUnhelpfulInsightText } from "../utils/format";
import CommentsPanel from "../components/CommentsPanel";

export default function TopicDeepDive() {
  const { topicId } = useParams<{ topicId: string }>();
  const id = topicId ? parseInt(topicId, 10) : NaN;
  const validId = !isNaN(id) && id > 0;

  const { data: topic, isLoading, error } = useQuery({
    queryKey: ["topic", id],
    queryFn: () => fetchTopic(id),
    enabled: validId,
  });
  const { data: discussions } = useQuery({
    queryKey: ["discussions", id],
    queryFn: () => fetchTopicDiscussions(id),
    enabled: validId,
  });
  const { data: momentum } = useQuery({
    queryKey: ["momentum", id],
    queryFn: () => fetchMomentum(id),
    enabled: validId,
  });

  if (!validId) {
    return (
      <div>
        <Card>
          <CardBody>
            <p className="text-rose-300 font-medium">Invalid topic ID.</p>
            <Link to="/dashboard" className="text-cyan-200 hover:text-cyan-100 text-sm font-medium">
              Back to Dashboard →
            </Link>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (isLoading || !topic) {
    return (
      <div className="py-8">
        <Spinner label="Loading topic…" />
      </div>
    );
  }
  if (error) {
    return (
      <div>
        <Card>
          <CardBody>
            <p className="text-rose-300 font-medium">{(error as Error).message}</p>
            <Link to="/dashboard" className="text-cyan-200 hover:text-cyan-100 text-sm font-medium">
              Back to Dashboard →
            </Link>
          </CardBody>
        </Card>
      </div>
    );
  }

  const insight = topic.trend_insight;

  return (
    <div>
      <nav className="text-sm text-white/60 mb-6">
        <Link to="/dashboard" className="hover:text-white">
          Dashboard
        </Link>
        <span className="mx-2">→</span>
        <span className="text-white/85">{humanizeTopicLabel(topic.label) || `Topic ${topic.id}`}</span>
      </nav>

      <h2 className="font-display text-2xl font-semibold text-white mb-6">
        {humanizeTopicLabel(topic.label) || `Topic ${topic.id}`}
      </h2>
      {topic.category ? (
        <div className="mb-4">
          <Badge tone="slate">{humanizeToken(topic.category)}</Badge>
        </div>
      ) : null}

      {insight && (
        <Card className="mb-8">
          <CardHeader className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-white">Trend insight</p>
              <p className="text-xs text-white/55 mt-1">Short AI summary (updates after you “Update signals”).</p>
            </div>
          </CardHeader>
          <CardBody className="space-y-4">
          {insight.summary && !isUnhelpfulInsightText(insight.summary) && (
            <div>
              <h3 className="text-white/65 font-medium text-sm mb-1">What it is</h3>
              <p className="text-white/85">{displayInsightText(insight.summary)}</p>
            </div>
          )}
          {insight.why_it_matters && !isUnhelpfulInsightText(insight.why_it_matters) && (
            <div>
              <h3 className="text-white/65 font-medium text-sm mb-1">Why it matters</h3>
              <p className="text-white/85">{displayInsightText(insight.why_it_matters)}</p>
            </div>
          )}
          {insight.industry_impact && !isUnhelpfulInsightText(insight.industry_impact) && (
            <div>
              <h3 className="text-white/65 font-medium text-sm mb-1">Potential impact</h3>
              <p className="text-white/85">{displayInsightText(insight.industry_impact)}</p>
            </div>
          )}
          {insight &&
            [insight.summary, insight.why_it_matters, insight.industry_impact].every(
              (x) => !x?.trim() || isUnhelpfulInsightText(x)
            ) && (
              <p className="text-white/60 text-sm">
                No AI write-up for this topic yet — see related discussions below, or run <strong className="text-white/80">Update signals</strong> after more posts are ingested.
              </p>
            )}
          {"id" in insight && typeof (insight as any).id === "number" ? (
            <CommentsPanel signalId={(insight as any).id} />
          ) : null}
          </CardBody>
        </Card>
      )}

      {momentum && momentum.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-medium text-slate-800 mb-4">Momentum</h3>
          <div className="h-64 rounded-2xl border border-slate-200 bg-white p-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={momentum}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                <YAxis stroke="#64748b" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #cbd5e1" }}
                />
                <Line
                  type="monotone"
                  dataKey="mention_count"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Mentions"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="signal_score"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  name="Signal score"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div>
        <h3 className="text-lg font-medium text-slate-800 mb-4">Related discussions & research</h3>
        {discussions && discussions.length > 0 ? (
          <ul className="space-y-3">
            {discussions.map((d) => (
              <li key={d.id}>
                <Card className="hover:border-slate-300 transition-colors">
                  <CardBody className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge>{d.source}</Badge>
                          {d.author ? <span className="text-xs text-slate-500">by {d.author}</span> : null}
                        </div>
                        <p className="font-medium text-slate-900 truncate">{d.title || "No title"}</p>
                        {d.body ? (
                          <p className="text-slate-600 text-sm mt-1 line-clamp-2">{d.body}</p>
                        ) : null}
                      </div>
                      {d.url ? (
                        <a
                          href={d.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-emerald-700 hover:text-emerald-600 text-sm shrink-0 font-medium"
                        >
                          Open →
                        </a>
                      ) : null}
                    </div>
                  </CardBody>
                </Card>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-600">No discussions yet.</p>
        )}
      </div>
    </div>
  );
}
