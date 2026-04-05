import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createAlertRule, deleteAlertRule, fetchAlertEvents, fetchAlertRules, updateAlertRule } from "../api/client";
import type { AlertRuleOut } from "../api/client";
import { Badge, Button, Card, CardBody, CardHeader, SegmentedTabs, Spinner, cx } from "../components/ui";
import { humanizeToken } from "../utils/format";

const CATEGORY_OPTIONS = [
  { value: "", label: "Any category" },
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

type CategoryFormValue = (typeof CATEGORY_OPTIONS)[number]["value"];

const HEAT_OPTIONS = [
  { value: "warm", label: "Warming up", min: 0.3, hint: "More alerts, includes smaller moves" },
  { value: "solid", label: "Solid", min: 0.5, hint: "Balanced — good default" },
  { value: "hot", label: "Hot", min: 0.65, hint: "Only clearly trending topics" },
  { value: "very_hot", label: "Very hot", min: 0.8, hint: "Rare — strongest signals only" },
] as const;
type HeatValue = (typeof HEAT_OPTIONS)[number]["value"];

const PLACES_OPTIONS = [
  { value: "loose", label: "Loose", min: 0.1, hint: "Don’t require many platforms" },
  { value: "normal", label: "Normal", min: 0.25, hint: "A few different sources" },
  { value: "tight", label: "Tight", min: 0.45, hint: "Must show up in many places" },
] as const;
type PlacesValue = (typeof PLACES_OPTIONS)[number]["value"];

const inputClass =
  "mt-1.5 w-full rounded-xl border border-white/10 bg-black/20 px-3 h-11 text-sm text-white/90 placeholder:text-white/35 focus:outline-none focus:ring-2 focus:ring-cyan-400/25 focus:border-cyan-300/25";

const textareaClass =
  "mt-1.5 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2.5 min-h-[88px] text-sm text-white/90 placeholder:text-white/35 focus:outline-none focus:ring-2 focus:ring-cyan-400/25 focus:border-cyan-300/25";

function parseKeywordsInput(s: string): string[] | null {
  const parts = s
    .split(/[\n,;]+/)
    .map((x) => x.trim())
    .filter(Boolean);
  return parts.length ? parts : null;
}

function heatFromScore(score: number | null | undefined): HeatValue {
  if (score == null) return "solid";
  const exact = HEAT_OPTIONS.find((h) => Math.abs(h.min - score) < 0.001);
  return exact ? exact.value : "solid";
}

function placesFromMin(min: number | null | undefined): PlacesValue {
  if (min == null) return "normal";
  const exact = PLACES_OPTIONS.find((p) => Math.abs(p.min - min) < 0.001);
  return exact ? exact.value : "normal";
}

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

  const [editingId, setEditingId] = React.useState<number | null>(null);
  const [name, setName] = React.useState("");
  const [enabled, setEnabled] = React.useState(true);
  const [category, setCategory] = React.useState<CategoryFormValue>("");
  const [keywordsText, setKeywordsText] = React.useState("");
  const [heat, setHeat] = React.useState<HeatValue>("solid");
  const [places, setPlaces] = React.useState<PlacesValue>("normal");
  const [webhook, setWebhook] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [deletingId, setDeletingId] = React.useState<number | null>(null);
  const [formError, setFormError] = React.useState<string | null>(null);
  const [formOk, setFormOk] = React.useState<string | null>(null);

  const minScore = HEAT_OPTIONS.find((h) => h.value === heat)!.min;
  const minCross = PLACES_OPTIONS.find((p) => p.value === places)!.min;

  const ruleNameById = React.useMemo(() => {
    const m = new Map<number, string>();
    rules?.forEach((r) => m.set(r.id, r.name));
    return m;
  }, [rules]);

  const resetForm = () => {
    setEditingId(null);
    setName("");
    setEnabled(true);
    setCategory("");
    setKeywordsText("");
    setHeat("solid");
    setPlaces("normal");
    setWebhook("");
  };

  const beginEdit = (r: AlertRuleOut) => {
    setEditingId(r.id);
    setName(r.name);
    setEnabled(r.enabled);
    setCategory((r.category || "") as CategoryFormValue);
    setKeywordsText(r.keywords?.length ? r.keywords.join(", ") : "");
    setHeat(heatFromScore(r.min_signal_score ?? undefined));
    setPlaces(placesFromMin(r.min_cross_source_strength ?? undefined));
    setWebhook(r.webhook_url ?? "");
    setFormError(null);
    setFormOk(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const onSave = async () => {
    setFormError(null);
    setFormOk(null);
    const w = webhook.trim();
    if (!name.trim()) {
      setFormError("Give this alert a short name so you recognize it later.");
      return;
    }
    const keywords = parseKeywordsInput(keywordsText);
    setSaving(true);
    try {
      if (editingId != null) {
        await updateAlertRule(editingId, {
          name: name.trim(),
          enabled,
          category: category || null,
          keywords,
          min_signal_score: minScore,
          min_cross_source_strength: minCross,
          webhook_url: w ? w : null,
          max_events_per_day: 20,
        });
        setFormOk("Alert updated.");
      } else {
        await createAlertRule({
          name: name.trim(),
          enabled: true,
          category: category || null,
          keywords,
          min_signal_score: minScore,
          min_cross_source_strength: minCross,
          webhook_url: w ? w : null,
          max_events_per_day: 20,
        });
        setWebhook("");
        setFormOk(
          w
            ? "Alert saved. We’ll check about every 10 minutes and notify you in the app and via your webhook when something matches."
            : "Alert saved. We’ll check about every 10 minutes and show matches in the app (header bell)."
        );
      }
      await qc.invalidateQueries({ queryKey: ["alert-rules"] });
      await qc.invalidateQueries({ queryKey: ["alert-events"] });
      if (!editingId) {
        setName("");
        setCategory("");
        setKeywordsText("");
      }
    } catch (e) {
      setFormError((e as Error).message || "Couldn’t save. Check that the API is running.");
    } finally {
      setSaving(false);
    }
  };

  const onDelete = async (id: number) => {
    if (!window.confirm("Delete this alert rule? Past notifications stay in history.")) return;
    setDeletingId(id);
    try {
      await deleteAlertRule(id);
      if (editingId === id) resetForm();
      await qc.invalidateQueries({ queryKey: ["alert-rules"] });
      await qc.invalidateQueries({ queryKey: ["alert-events"] });
    } catch (e) {
      alert((e as Error).message || "Delete failed.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-xl sm:text-2xl font-semibold text-white">Alerts</h2>
        <p className="text-[13px] sm:text-sm text-white/70 mt-1 max-w-2xl">
          Get notified when a trend matches what you care about. Use optional <strong className="text-white/85">keywords</strong>{" "}
          (e.g. <em className="text-white/80">book, reading</em>) so alerts are not limited to preset categories. By default
          notifications appear in the app (header bell); add a webhook if you also want Slack or Discord.
        </p>
      </div>

      <Card>
        <CardHeader>
          <div>
            <p className="text-white font-medium">{editingId != null ? `Edit alert #${editingId}` : "Create an alert"}</p>
            <p className="text-xs text-white/55 mt-1">
              {editingId != null
                ? "Update the fields below and save, or cancel to discard changes."
                : "You can create several rules (e.g. one for books, one for security)."}
            </p>
          </div>
        </CardHeader>
        <CardBody className="space-y-5">
          {editingId != null ? (
            <label className="flex items-center gap-2 text-sm text-white/80 cursor-pointer">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                className="rounded border-white/20 bg-black/30"
              />
              Enabled
            </label>
          ) : null}

          <label className="block text-sm text-white/80">
            Name <span className="text-rose-300">*</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder='e.g. "Books & publishing"'
              className={inputClass}
            />
            <span className="text-xs text-white/45 mt-1 block">Only you see this — it labels the rule in the list below.</span>
          </label>

          <div>
            <p className="text-sm text-white/80 mb-2">Topic category (optional)</p>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as CategoryFormValue)}
              className={cx(inputClass, "cursor-pointer")}
            >
              {CATEGORY_OPTIONS.map((o) => (
                <option key={o.value || "any"} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-white/45 mt-1.5">
              {category ? `Narrow to topics tagged “${humanizeToken(category)}”.` : "Any category — combine with keywords below."}
            </p>
          </div>

          <label className="block text-sm text-white/80">
            Keywords <span className="text-white/40 font-normal">(optional)</span>
            <textarea
              value={keywordsText}
              onChange={(e) => setKeywordsText(e.target.value)}
              placeholder={'e.g. book, reading, novel — separate with commas or new lines. All terms must appear in the topic title or insight text.'}
              className={textareaClass}
            />
            <span className="text-xs text-white/45 mt-1 block">
              Matching is case-insensitive. Leave empty to match only on category + strength rules above.
            </span>
          </label>

          <div>
            <p className="text-sm text-white/80 mb-2">How strong should the trend be?</p>
            <p className="text-xs text-white/45 mb-2">Higher = fewer alerts, but each one is a stronger signal.</p>
            <SegmentedTabs
              value={heat}
              onChange={(v) => setHeat(v as HeatValue)}
              options={HEAT_OPTIONS.map((h) => ({ value: h.value, label: h.label }))}
            />
            <p className="text-xs text-white/45 mt-2">{HEAT_OPTIONS.find((h) => h.value === heat)?.hint}</p>
          </div>

          <div>
            <p className="text-sm text-white/80 mb-2">How many platforms should mention it?</p>
            <p className="text-xs text-white/45 mb-2">Raises the bar so you only hear about topics discussed in more than one place.</p>
            <SegmentedTabs
              value={places}
              onChange={(v) => setPlaces(v as PlacesValue)}
              options={PLACES_OPTIONS.map((p) => ({ value: p.value, label: p.label }))}
            />
            <p className="text-xs text-white/45 mt-2">{PLACES_OPTIONS.find((p) => p.value === places)?.hint}</p>
          </div>

          <label className="block text-sm text-white/80">
            Webhook URL <span className="text-white/40 font-normal">(optional)</span>
            <input
              value={webhook}
              onChange={(e) => setWebhook(e.target.value)}
              placeholder="Leave blank for in-app only, or paste a Slack / Discord webhook URL"
              className={inputClass}
            />
            <span className="text-xs text-white/45 mt-1 block">
              In-app notifications always apply. If you add a URL, we also POST one JSON payload per match.
            </span>
          </label>

          {formError ? <p className="text-sm text-rose-300">{formError}</p> : null}
          {formOk ? <p className="text-sm text-emerald-300/90">{formOk}</p> : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={() => void onSave()} disabled={saving}>
              {saving ? "Saving…" : editingId != null ? "Save changes" : "Save alert"}
            </Button>
            {editingId != null ? (
              <Button type="button" variant="ghost" onClick={resetForm} disabled={saving}>
                Cancel edit
              </Button>
            ) : null}
            <span className="text-xs text-white/45">Checks run about every 10 minutes · up to 20 notifications per rule per day</span>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <p className="text-white font-medium">Your alerts</p>
            <p className="text-xs text-white/50 mt-0.5">Rules you’ve created — edit or delete anytime</p>
          </div>
          {rulesLoading ? <Spinner label="Loading…" /> : null}
        </CardHeader>
        <CardBody>
          {rulesError ? <p className="text-rose-300 text-sm">{(rulesError as Error).message}</p> : null}
          {rules?.length ? (
            <ul className="space-y-3">
              {rules.map((r) => (
                <li key={r.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-white font-medium truncate">{r.name}</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        <Badge tone={r.enabled ? "emerald" : "amber"}>{r.enabled ? "On" : "Off"}</Badge>
                        {r.category ? (
                          <Badge tone="slate">{humanizeToken(r.category)}</Badge>
                        ) : (
                          <Badge tone="slate">Any category</Badge>
                        )}
                        {r.keywords?.length ? (
                          <Badge tone="amber" title="All keywords must match in insight text">
                            Keywords: {r.keywords.join(" · ")}
                          </Badge>
                        ) : null}
                        {r.min_signal_score != null ? (
                          <Badge tone="emerald" title="Minimum trend strength">
                            Strength ≥ {r.min_signal_score}
                          </Badge>
                        ) : null}
                        {r.min_cross_source_strength != null ? (
                          <Badge tone="sky" title="Seen across sources">
                            Many places ≥ {r.min_cross_source_strength}
                          </Badge>
                        ) : null}
                        {r.webhook_url ? (
                          <Badge tone="slate" title="Also posts to webhook">
                            + Webhook
                          </Badge>
                        ) : (
                          <Badge tone="sky">In-app only</Badge>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <span className="text-xs text-white/40">#{r.id}</span>
                      <div className="flex gap-2">
                        <Button type="button" variant="ghost" className="!h-8 !px-3 !text-xs" onClick={() => beginEdit(r)}>
                          Edit
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          className="!h-8 !px-3 !text-xs text-rose-300/90 hover:text-rose-200"
                          onClick={() => void onDelete(r.id)}
                          disabled={deletingId === r.id}
                        >
                          {deletingId === r.id ? "…" : "Delete"}
                        </Button>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : !rulesLoading ? (
            <p className="text-white/55 text-sm">No alerts yet — create one above.</p>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <div>
            <p className="text-white font-medium">Recent notifications</p>
            <p className="text-xs text-white/50 mt-0.5">In-app history (and webhook status when configured)</p>
          </div>
          {eventsLoading ? <Spinner label="Loading…" /> : null}
        </CardHeader>
        <CardBody>
          {events?.length ? (
            <ul className="space-y-3">
              {events.map((e) => (
                <li key={e.id} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={e.status === "sent" ? "emerald" : "amber"}>{e.status === "sent" ? "OK" : "Issue"}</Badge>
                    <span className="text-white/85 text-sm">
                      {e.rule_name || (e.rule_id != null ? ruleNameById.get(e.rule_id) : undefined) ? (
                        <>
                          <span className="text-white/55">Alert </span>“
                          {e.rule_name ?? (e.rule_id != null ? ruleNameById.get(e.rule_id) : "Deleted rule")}
                          ”
                        </>
                      ) : (
                        <>Alert {e.rule_id != null ? `#${e.rule_id}` : "(deleted rule)"}</>
                      )}
                      <span className="text-white/55">
                        {" "}
                        · {e.topic_label ?? `topic #${e.topic_id}`}
                      </span>
                    </span>
                    <span className="text-xs text-white/40">{new Date(e.sent_at).toLocaleString()}</span>
                  </div>
                  {e.error_message ? <p className="text-rose-300 text-sm mt-2">{e.error_message}</p> : null}
                </li>
              ))}
            </ul>
          ) : !eventsLoading ? (
            <p className="text-white/55 text-sm">Nothing sent yet — when a rule matches, it will show here.</p>
          ) : null}
        </CardBody>
      </Card>
    </div>
  );
}
