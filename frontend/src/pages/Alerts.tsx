import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createAlertRule, fetchAlertEvents, fetchAlertRules } from "../api/client";
import { Badge, Button, Card, CardBody, CardHeader, Spinner } from "../components/ui";

export default function AlertsPage() {
  const qc = useQueryClient();
  const { data: rules, isLoading: rulesLoading, error: rulesError } = useQuery({
    queryKey: ["alert-rules"],
    queryFn: fetchAlertRules,
  });
  const { data: events, isLoading: eventsLoading } = useQuery({
    queryKey: ["alert-events"],
    queryFn: () => fetchAlertEvents(50),
    refetchInterval: 30_000,
  });

  const [name, setName] = React.useState("High-signal AI Models");
  const [category, setCategory] = React.useState<string>("ai_models");
  const [minScore, setMinScore] = React.useState<number>(0.7);
  const [minCross, setMinCross] = React.useState<number>(0.2);
  const [webhook, setWebhook] = React.useState<string>("");
  const [saving, setSaving] = React.useState(false);

  const onCreate = async () => {
    setSaving(true);
    try {
      await createAlertRule({
        name,
        enabled: true,
        category: category || null,
        min_signal_score: minScore,
        min_cross_source_strength: minCross,
        webhook_url: webhook,
        max_events_per_day: 20,
      });
      await qc.invalidateQueries({ queryKey: ["alert-rules"] });
      setWebhook("");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl sm:text-2xl font-semibold text-white">Alerts</h2>
        <p className="text-[13px] sm:text-sm text-white/70 mt-1">
          Create watch rules and send alerts to a webhook (Slack/Discord/custom).
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-slate-200 font-medium">Create rule</p>
              <p className="text-xs text-slate-500 mt-1">
                Tip: use a Slack incoming webhook URL. Alerts are evaluated every ~10 minutes.
              </p>
            </div>
          </div>
        </CardHeader>
        <CardBody className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm text-slate-300">
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950/30 px-3 h-10 text-slate-100"
            />
          </label>
          <label className="text-sm text-slate-300">
            Category
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="ai_models"
              className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950/30 px-3 h-10 text-slate-100"
            />
          </label>
          <label className="text-sm text-slate-300">
            Min signal score
            <input
              type="number"
              step="0.05"
              value={minScore}
              onChange={(e) => setMinScore(parseFloat(e.target.value))}
              className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950/30 px-3 h-10 text-slate-100"
            />
          </label>
          <label className="text-sm text-slate-300">
            Min cross-source
            <input
              type="number"
              step="0.05"
              value={minCross}
              onChange={(e) => setMinCross(parseFloat(e.target.value))}
              className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950/30 px-3 h-10 text-slate-100"
            />
          </label>
          <label className="text-sm text-slate-300 sm:col-span-2">
            Webhook URL
            <input
              value={webhook}
              onChange={(e) => setWebhook(e.target.value)}
              placeholder="https://hooks.slack.com/services/..."
              className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950/30 px-3 h-10 text-slate-100"
            />
          </label>
          <div className="sm:col-span-2">
            <Button onClick={onCreate} disabled={saving || !webhook}>
              {saving ? "Saving…" : "Create rule"}
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <p className="text-slate-200 font-medium">Rules</p>
          {rulesLoading ? <Spinner label="Loading…" /> : null}
        </CardHeader>
        <CardBody>
          {rulesError ? <p className="text-rose-400 text-sm">{(rulesError as Error).message}</p> : null}
          {rules?.length ? (
            <ul className="space-y-2">
              {rules.map((r) => (
                <li key={r.id} className="rounded-xl border border-slate-800 bg-slate-950/30 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-slate-100 font-medium truncate">{r.name}</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        <Badge tone={r.enabled ? "emerald" : "amber"}>{r.enabled ? "enabled" : "disabled"}</Badge>
                        {r.category ? <Badge>{r.category}</Badge> : null}
                        {r.min_signal_score != null ? <Badge tone="emerald">score ≥ {r.min_signal_score}</Badge> : null}
                        {r.min_cross_source_strength != null ? <Badge tone="sky">cross ≥ {r.min_cross_source_strength}</Badge> : null}
                      </div>
                    </div>
                    <span className="text-xs text-slate-500 shrink-0">#{r.id}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">No rules yet.</p>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <p className="text-slate-200 font-medium">Recent events</p>
          {eventsLoading ? <Spinner label="Loading…" /> : null}
        </CardHeader>
        <CardBody>
          {events?.length ? (
            <ul className="space-y-2">
              {events.map((e) => (
                <li key={e.id} className="rounded-xl border border-slate-800 bg-slate-950/30 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={e.status === "sent" ? "emerald" : "amber"}>{e.status}</Badge>
                    <span className="text-slate-300 text-sm">
                      rule #{e.rule_id} → topic #{e.topic_id}
                    </span>
                    <span className="text-xs text-slate-500">{new Date(e.sent_at).toLocaleString()}</span>
                  </div>
                  {e.error_message ? <p className="text-rose-400 text-sm mt-2">{e.error_message}</p> : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-500 text-sm">No events yet.</p>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

