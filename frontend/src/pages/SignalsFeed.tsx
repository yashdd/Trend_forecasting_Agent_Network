import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchSignals, triggerPipeline } from "../api/client";
import { formatDistanceToNow } from "date-fns";
import { Badge, Button, Card, CardBody, CardHeader, SegmentedTabs, Spinner, cx } from "../components/ui";
import ExplainPanel from "../components/ExplainPanel";
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

export default function SignalsFeed() {
  const [minScore, setMinScore] = React.useState(0);
  const [category, setCategory] = React.useState<CategoryValue>("all");
  const [pipelineRunning, setPipelineRunning] = React.useState(false);
  const [openExplainFor, setOpenExplainFor] = React.useState<number | null>(null);
  const queryClient = useQueryClient();
  const { data: signals, isLoading, error } = useQuery({
    queryKey: ["signals", minScore, category],
    queryFn: () =>
      fetchSignals({
        limit: 30,
        min_score: minScore,
        category: category === "all" ? undefined : category,
      }),
  });

  const runPipeline = async () => {
    setPipelineRunning(true);
    try {
      await triggerPipeline();
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["signals"] });
        setPipelineRunning(false);
      }, 2000);
    } catch (e) {
      setPipelineRunning(false);
      console.error(e);
    }
  };

  return (
    <div>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between mb-6">
        <div className="min-w-0">
          <h2 className="font-display text-xl sm:text-2xl font-semibold text-white">Signals</h2>
          <p className="text-[13px] sm:text-sm text-white/70 mt-1">
            Fresh clusters with momentum + cross-platform confirmation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={runPipeline} disabled={pipelineRunning} variant="secondary">
            {pipelineRunning ? "Pipeline started…" : "Run pipeline now"}
          </Button>
          <Button
            onClick={() => queryClient.invalidateQueries({ queryKey: ["signals"] })}
            variant="ghost"
            title="Refresh"
          >
            Refresh
          </Button>
        </div>
      </div>

      <Card className="mb-6">
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <SegmentedTabs
            value={category}
            onChange={setCategory}
            options={CATEGORY_OPTIONS as unknown as Array<{ value: CategoryValue; label: string }>}
            className="max-w-full overflow-x-auto"
          />
          <div className="flex items-center gap-3">
            <label className="text-white/70 text-sm">Min score</label>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={minScore}
              onChange={(e) => setMinScore(parseFloat(e.target.value))}
              className="w-40 accent-emerald-500"
            />
            <Badge tone="emerald">{minScore.toFixed(2)}+</Badge>
          </div>
        </CardHeader>
        <CardBody className="flex items-center justify-between gap-4 text-sm">
          <div className="text-white/70">
            Tip: higher cross-source strength means the topic appears across more platforms.
          </div>
          <div className="text-white/55">
            {signals ? `${signals.length} items` : null}
          </div>
        </CardBody>
      </Card>

      {isLoading && (
        <div className="py-8">
          <Spinner label="Loading signals…" />
        </div>
      )}
      {error && <p className="text-rose-400">Failed to load: {(error as Error).message}</p>}

      {signals && signals.length === 0 && (
        <Card className="p-8 text-center">
          <div className="max-w-xl mx-auto">
            <p className="text-white font-medium">No signals yet</p>
            <p className="text-white/70 text-sm mt-2">
              Run the pipeline to ingest from 10 platforms, cluster discussions, and generate trend insights.
            </p>
            <div className="mt-5 flex items-center justify-center gap-2">
              <Button type="button" onClick={runPipeline} disabled={pipelineRunning}>
                {pipelineRunning ? "Pipeline started…" : "Run pipeline now"}
              </Button>
              <Button
                type="button"
                onClick={() => queryClient.invalidateQueries({ queryKey: ["signals"] })}
                variant="secondary"
              >
                Refresh
              </Button>
            </div>
            <p className="text-white/55 text-xs mt-3">It runs in the background; refresh in a few minutes.</p>
          </div>
        </Card>
      )}

      <ul className="space-y-4">
        {signals?.map((s) => (
          <li key={s.id}>
            <Card className="hover:border-white/20 transition-colors">
              <CardBody className="p-5">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-display font-semibold text-white">
                      {humanizeToken(s.topic_label) || `Topic ${s.topic_id}`}
                    </span>
                    {s.category ? <Badge tone="slate">{humanizeToken(s.category)}</Badge> : null}
                    {s.signal_score != null ? (
                      <Badge tone="emerald" className="cursor-help" title="Trend score: 0 to 1. Bigger means hotter right now.">
                        Hot {s.signal_score.toFixed(2)}
                      </Badge>
                    ) : null}
                    {s.cross_source_strength != null ? (
                      <Badge tone="sky" className="cursor-help" title="Seen in many places: higher means more different platforms talk about it.">
                        Many places {s.cross_source_strength.toFixed(2)}
                      </Badge>
                    ) : null}
                    {s.predicted_impact ? <Badge tone="amber">{s.predicted_impact}</Badge> : null}
                  </div>

                  {s.summary ? (
                    <p className="text-white/80 text-sm leading-relaxed line-clamp-3">{s.summary}</p>
                  ) : (
                    <p className="text-white/55 text-sm">No summary yet (LLM synthesis runs after clustering).</p>
                  )}

                  <div className="flex flex-wrap gap-2">
                    {s.sources?.slice(0, 8).map((src, i) => (
                      <span
                        key={i}
                        className={cx(
                          "rounded-lg border border-white/10 bg-white/5 text-white/70 text-xs px-2 py-1"
                        )}
                      >
                        {src.name}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between gap-3 text-xs text-white/55">
                    <div className="min-w-0">
                      {s.updated_at ? (
                        <span>Updated {formatDistanceToNow(new Date(s.updated_at), { addSuffix: true })}</span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setOpenExplainFor(openExplainFor === s.topic_id ? null : s.topic_id)}
                        className="text-white/70 hover:text-white font-medium"
                      >
                        Explain like I’m 5
                      </button>
                      <Link to={`/topics/${s.topic_id}`} className="text-cyan-200 hover:text-cyan-100 font-medium">
                        View deep-dive →
                      </Link>
                    </div>
                  </div>

                  {openExplainFor === s.topic_id ? <ExplainPanel topicId={s.topic_id} /> : null}
                </div>
              </CardBody>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
