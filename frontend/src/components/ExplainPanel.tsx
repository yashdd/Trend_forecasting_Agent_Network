import { useQuery } from "@tanstack/react-query";
import { fetchExplainability } from "../api/client";
import { Badge, Card, CardBody, Spinner } from "./ui";

export default function ExplainPanel(props: { topicId: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["explain", props.topicId],
    queryFn: () => fetchExplainability(props.topicId),
  });

  if (isLoading) return <Spinner label="Loading why-trending…" />;
  if (error) return <p className="text-rose-400 text-sm">{(error as Error).message}</p>;
  if (!data) return null;

  return (
    <Card className="mt-3">
      <CardBody className="space-y-3">
        <div className="flex flex-wrap gap-2 items-center">
          <Badge tone="slate">Why this is hot (simple)</Badge>
          {data.source_families?.map((f) => (
            <Badge key={f} tone="sky">
              {f}
            </Badge>
          ))}
        </div>

        {data.mention_count_today != null ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-slate-900 text-sm font-medium">How much people are talking about it</p>
            <p className="text-slate-700 text-sm mt-1">
              Today: <span className="font-semibold text-slate-900">{data.mention_count_today}</span>{" "}
              {data.mention_count_yesterday != null ? (
                <span className="text-slate-600">(yesterday {data.mention_count_yesterday})</span>
              ) : null}
            </p>
          </div>
        ) : null}

        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-slate-900 text-sm font-medium">Trend score</p>
            <p className="text-slate-700 text-sm mt-1">
              A number from <span className="font-semibold">0 to 1</span>. Bigger = more “hot right now”.
            </p>
            {data.signal_score != null ? (
              <p className="text-slate-900 text-lg font-display font-semibold mt-2">{data.signal_score.toFixed(2)}</p>
            ) : null}
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <p className="text-slate-900 text-sm font-medium">Seen in many places</p>
            <p className="text-slate-700 text-sm mt-1">
              This is “how many different places” talk about the same thing.
            </p>
            {data.cross_source_strength != null ? (
              <p className="text-slate-900 text-lg font-display font-semibold mt-2">
                {data.cross_source_strength.toFixed(2)}
              </p>
            ) : null}
          </div>
        </div>

        <details className="rounded-2xl border border-slate-200 bg-white p-4">
          <summary className="cursor-pointer text-sm font-medium text-slate-900">
            What do “growth” and “acceleration” mean?
          </summary>
          <div className="mt-3 text-sm text-slate-700 space-y-2">
            <p>
              <span className="font-medium">Growth</span> = “Are people talking more than yesterday?”
            </p>
            <p>
              <span className="font-medium">Acceleration</span> = “Is it speeding up even more?”
            </p>
            <p className="text-slate-600">
              Think of a toy car: growth is how fast it is, acceleration is how much you press the gas.
            </p>
            <div className="flex flex-wrap gap-2 text-xs text-slate-600">
              {data.growth_rate != null ? <span>growth {data.growth_rate.toFixed(2)}</span> : null}
              {data.acceleration != null ? <span>accel {data.acceleration.toFixed(2)}</span> : null}
            </div>
          </div>
        </details>

        {data.top_phrases?.length ? (
          <div className="flex flex-wrap gap-2">
            {data.top_phrases.map((p) => (
              <Badge key={p}>{p}</Badge>
            ))}
          </div>
        ) : null}

        {data.evidence?.length ? (
          <div className="space-y-2">
            <p className="text-xs text-slate-500">
              Proof (click to see where we got it)
            </p>
            <ul className="space-y-2">
              {data.evidence.slice(0, 5).map((e) => (
                <li
                  key={`${e.source}-${e.raw_post_id}`}
                  className="rounded-2xl border border-slate-200 bg-white p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Badge>{e.source}</Badge>
                        <Badge tone="sky">{e.source_family}</Badge>
                      </div>
                      {e.title ? <p className="text-slate-900 text-sm font-medium truncate mt-1">{e.title}</p> : null}
                      {e.excerpt ? <p className="text-slate-600 text-sm mt-1 line-clamp-2">{e.excerpt}</p> : null}
                    </div>
                    {e.url ? (
                      <a
                        href={e.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-emerald-700 hover:text-emerald-600 text-sm font-medium shrink-0"
                      >
                        Open →
                      </a>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}

