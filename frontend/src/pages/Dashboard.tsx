import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchTopics, fetchTopic, fetchMomentum } from "../api/client";
import { useState } from "react";
import { Badge, Card, CardBody, CardHeader, SegmentedTabs, Spinner } from "../components/ui";
import { humanizeToken } from "../utils/format";

const CATEGORY_OPTIONS = [
  { value: "all", label: "All" },
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
type CategoryValue = (typeof CATEGORY_OPTIONS)[number]["value"];

export default function Dashboard() {
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [category, setCategory] = useState<CategoryValue>("all");
  const { data: topics, isLoading: topicsLoading } = useQuery({
    queryKey: ["topics", 7, "signal_score", category],
    queryFn: () =>
      fetchTopics({
        days: 7,
        sort: "signal_score",
        limit: 30,
        category: category === "all" ? undefined : category,
      }),
  });
  const { data: topicDetail } = useQuery({
    queryKey: ["topic", selectedTopicId],
    queryFn: () => fetchTopic(selectedTopicId!),
    enabled: selectedTopicId != null,
  });
  const { data: momentum } = useQuery({
    queryKey: ["momentum", selectedTopicId],
    queryFn: () => fetchMomentum(selectedTopicId!),
    enabled: selectedTopicId != null,
  });

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="font-display text-xl sm:text-2xl font-semibold text-white">Dashboard</h2>
          <p className="text-[13px] sm:text-sm text-white/70 mt-1">Pick a topic to see its momentum curve and deep-dive.</p>
        </div>
        <SegmentedTabs
          value={category}
          onChange={setCategory}
          options={CATEGORY_OPTIONS as unknown as Array<{ value: CategoryValue; label: string }>}
          className="max-w-full overflow-x-auto"
        />
      </div>

      <section className="mb-10">
        <Card>
          <CardHeader className="flex items-center justify-between gap-4">
            <h3 className="text-lg font-medium text-white">Trending topics</h3>
            {topicsLoading ? <Spinner label="Loading…" /> : null}
          </CardHeader>
          <CardBody>
            {topics && topics.length === 0 ? (
              <p className="text-white/60 text-sm">No topics yet. Run the pipeline to generate clusters.</p>
            ) : null}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {topics?.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelectedTopicId(t.id)}
                  className={`rounded-2xl border p-4 text-left transition-colors ${
                    selectedTopicId === t.id
                      ? "border-cyan-300/40 bg-white/6"
                      : "border-white/10 bg-white/4 hover:border-white/20"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="font-medium text-white truncate">
                      {humanizeToken(t.label) || `Topic ${t.id}`}
                    </div>
                    {t.category ? <Badge>{humanizeToken(t.category)}</Badge> : null}
                  </div>
                  <div className="flex gap-2 mt-2 flex-wrap items-center">
                    {t.signal_score != null ? <Badge tone="emerald">Score {t.signal_score.toFixed(2)}</Badge> : null}
                    {t.cross_source_strength != null ? (
                      <Badge tone="sky">Cross {t.cross_source_strength.toFixed(2)}</Badge>
                    ) : null}
                    {t.mention_count != null ? <span className="text-xs text-white/65">{t.mention_count} mentions</span> : null}
                  </div>
                </button>
              ))}
            </div>
          </CardBody>
        </Card>
      </section>

      {selectedTopicId && (
        <section className="mb-10">
          <h3 className="text-lg font-medium text-white mb-4">
            Topic momentum — {humanizeToken(topicDetail?.label) || `Topic ${selectedTopicId}`}
          </h3>
          {momentum && momentum.length > 0 ? (
            <div className="h-72 rounded-2xl border border-white/10 bg-white/4 p-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={momentum}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.10)" />
                  <XAxis dataKey="date" stroke="rgba(234,240,255,0.65)" fontSize={12} />
                  <YAxis stroke="rgba(234,240,255,0.65)" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0b1022", border: "1px solid rgba(255,255,255,0.12)" }}
                    labelStyle={{ color: "rgba(234,240,255,0.9)" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="mention_count"
                    stroke="#22d3ee"
                    strokeWidth={2}
                    name="Mentions"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="signal_score"
                    stroke="#a78bfa"
                    strokeWidth={2}
                    name="Signal score"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-white/65">No momentum data for this topic.</p>
          )}
          <div className="mt-4 flex gap-4">
            <Link
              to={`/topics/${selectedTopicId}`}
              className="text-cyan-200 hover:text-cyan-100 font-medium"
            >
              Open topic deep-dive →
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
