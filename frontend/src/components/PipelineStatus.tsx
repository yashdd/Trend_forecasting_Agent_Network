import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { LAST_PIPELINE_TRIGGERED_AT_KEY, fetchLatestRun } from "../api/client";
import { Badge, cx } from "./ui";

export default function PipelineStatus(props: { className?: string }) {
  const { data: latest } = useQuery({
    queryKey: ["latest-run"],
    queryFn: fetchLatestRun,
    refetchInterval: 30_000,
  });

  let lastTriggeredAt: Date | null = null;
  try {
    const s = localStorage.getItem(LAST_PIPELINE_TRIGGERED_AT_KEY);
    if (s) lastTriggeredAt = new Date(s);
  } catch {
    lastTriggeredAt = null;
  }

  return (
    <div className={cx("flex items-center gap-2", props.className)}>
      {latest?.status ? (
        <Badge
          tone={latest.status === "success" ? "emerald" : latest.status === "failed" ? "amber" : "slate"}
          className="capitalize"
        >
          {latest.status === "running" ? "Updating" : latest.status === "success" ? "Updated" : "Needs attention"}
        </Badge>
      ) : null}
      <span className="text-xs text-white/55 hidden md:inline">
        {lastTriggeredAt ? `Last run ${formatDistanceToNow(lastTriggeredAt, { addSuffix: true })}` : "No run yet"}
      </span>
    </div>
  );
}
