import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchAlertEvents, LAST_SEEN_ALERT_EVENT_ID_KEY } from "../api/client";
import { cx } from "./ui";

function readLastSeenId(): number | null {
  try {
    const v = localStorage.getItem(LAST_SEEN_ALERT_EVENT_ID_KEY);
    if (v == null) return null;
    const n = parseInt(v, 10);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

function writeLastSeenId(id: number) {
  try {
    localStorage.setItem(LAST_SEEN_ALERT_EVENT_ID_KEY, String(id));
  } catch {
    // ignore
  }
}

/**
 * Navbar bell: polls alert events and shows a count of unseen deliveries.
 * First visit seeds last-seen to the newest id so the backlog doesn’t flood the badge.
 */
export default function AlertBell() {
  const { data: events } = useQuery({
    queryKey: ["alert-events"],
    queryFn: () => fetchAlertEvents(40),
    refetchInterval: 45_000,
  });

  const [watermark, setWatermark] = React.useState<number | null>(() => readLastSeenId());
  const [open, setOpen] = React.useState(false);
  const rootRef = React.useRef<HTMLDivElement>(null);
  const initDone = React.useRef(false);

  React.useEffect(() => {
    if (!events?.length) return;
    const maxId = Math.max(...events.map((e) => e.id));
    if (!initDone.current) {
      initDone.current = true;
      if (watermark == null) {
        writeLastSeenId(maxId);
        setWatermark(maxId);
      }
    }
  }, [events, watermark]);

  const unread =
    events?.filter((e) => (watermark == null ? false : e.id > watermark)).length ?? 0;

  React.useEffect(() => {
    if (!open) return;
    const onDoc = (ev: MouseEvent) => {
      if (!rootRef.current?.contains(ev.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const markAllRead = () => {
    if (!events?.length) return;
    const maxId = Math.max(...events.map((e) => e.id));
    writeLastSeenId(maxId);
    setWatermark(maxId);
    setOpen(false);
  };

  const onOpenItem = (eventId: number) => {
    const next = Math.max(watermark ?? 0, eventId);
    writeLastSeenId(next);
    setWatermark(next);
    setOpen(false);
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cx(
          "relative h-10 w-10 rounded-2xl border border-white/10 bg-white/5 flex items-center justify-center",
          "text-white/80 hover:text-white hover:bg-white/10 transition-colors",
          open && "ring-2 ring-cyan-400/30 border-cyan-300/20"
        )}
        aria-label={unread > 0 ? `${unread} unread alerts` : "Alerts"}
        aria-expanded={open}
      >
        <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" aria-hidden>
          <path
            d="M12 3a5 5 0 00-5 5v2.5L5 14h14l-2-3.5V8a5 5 0 00-5-5z"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinejoin="round"
          />
          <path d="M9 18h6a3 3 0 01-6 0z" stroke="currentColor" strokeWidth="1.75" strokeLinejoin="round" />
        </svg>
        {unread > 0 ? (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-[10px] font-bold text-white flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </button>

      {open ? (
        <div
          className={cx(
            "absolute right-0 mt-2 w-[min(100vw-2rem,22rem)] rounded-2xl border border-white/10",
            "bg-[#0a1220] shadow-[0_20px_50px_rgba(0,0,0,0.55)] z-50 overflow-hidden"
          )}
        >
          <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-white">Alert notifications</p>
            <button
              type="button"
              onClick={markAllRead}
              className="text-xs font-medium text-cyan-300/90 hover:text-cyan-200"
            >
              Mark read
            </button>
          </div>
          <div className="max-h-[min(70vh,320px)] overflow-y-auto">
            {events?.length ? (
              <ul className="divide-y divide-white/5">
                {events.map((e) => (
                  <li key={e.id}>
                    <Link
                      to={`/topics/${e.topic_id}`}
                      onClick={() => onOpenItem(e.id)}
                      className="block px-4 py-3 hover:bg-white/5 transition-colors"
                    >
                      <p className="text-sm text-white/90 leading-snug">
                        <span className="font-medium text-white">
                          {e.rule_name ?? (e.rule_id != null ? `Alert #${e.rule_id}` : "Deleted rule")}
                        </span>
                        <span className="text-white/50"> · </span>
                        <span>{e.topic_label ?? `Topic #${e.topic_id}`}</span>
                      </p>
                      <p className="text-[11px] text-white/40 mt-1">
                        {new Date(e.sent_at).toLocaleString()}
                        {e.status === "failed" ? (
                          <span className="text-rose-300/90 ml-2">Delivery issue</span>
                        ) : null}
                      </p>
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-4 py-6 text-sm text-white/50 text-center">No alerts yet</p>
            )}
          </div>
          <div className="px-4 py-2.5 border-t border-white/10 bg-black/20">
            <Link
              to="/alerts"
              onClick={() => setOpen(false)}
              className="text-xs font-medium text-cyan-300/90 hover:text-cyan-200"
            >
              Manage alert rules →
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
