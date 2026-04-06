import * as React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useLocation } from "react-router-dom";
import { fetchSignalsMeta, LAST_SEEN_SIGNAL_ID_KEY } from "../api/client";
import { cx } from "./ui";

function readLastSeenId(): number | null {
  try {
    const v = localStorage.getItem(LAST_SEEN_SIGNAL_ID_KEY);
    if (v == null) return null;
    const n = parseInt(v, 10);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

function writeLastSeenId(id: number) {
  try {
    localStorage.setItem(LAST_SEEN_SIGNAL_ID_KEY, String(id));
  } catch {
    // private mode / disabled storage
  }
}

/** Call after user views the feed or dismisses — sets watermark to current newest id. */
export async function markTrendsSeenNow(): Promise<void> {
  const meta = await fetchSignalsMeta();
  writeLastSeenId(meta.newest_insight_id);
}

/**
 * LinkedIn-style thin bar when newer signals exist than the last-seen watermark.
 * Uses GET /signals/meta (cheap) instead of full signal list payloads.
 */
export default function TrendNotificationBar() {
  const location = useLocation();
  const queryClient = useQueryClient();
  const [visible, setVisible] = React.useState(false);
  const [newCount, setNewCount] = React.useState(0);
  const initDone = React.useRef(false);

  const check = React.useCallback(async () => {
    try {
      const lastSeen = readLastSeenId();
      const meta = await fetchSignalsMeta(lastSeen ?? undefined);

      if (!initDone.current) {
        initDone.current = true;
        if (lastSeen == null) {
          writeLastSeenId(meta.newest_insight_id);
          setVisible(false);
          return;
        }
        if (meta.newer_count > 0) {
          setNewCount(meta.newer_count);
          setVisible(true);
        } else {
          setVisible(false);
        }
        return;
      }

      if (meta.newer_count > 0) {
        setNewCount(meta.newer_count);
        setVisible(true);
      } else {
        setVisible(false);
      }
    } catch {
      setVisible(false);
    }
  }, []);

  React.useEffect(() => {
    void check();
    const t = window.setInterval(() => void check(), 90_000);
    return () => window.clearInterval(t);
  }, [check]);

  React.useEffect(() => {
    if (location.pathname !== "/") return;
    let cancelled = false;
    const run = async () => {
      await new Promise((r) => setTimeout(r, 400));
      if (cancelled) return;
      await markTrendsSeenNow().catch(() => {});
      setVisible(false);
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  const onDismiss = React.useCallback(() => {
    void markTrendsSeenNow().finally(() => setVisible(false));
  }, []);

  const onOpenFeed = React.useCallback(() => {
    void markTrendsSeenNow().finally(() => {
      setVisible(false);
      if (location.pathname === "/") {
        void queryClient.invalidateQueries({ queryKey: ["signals"] });
      }
    });
  }, [location.pathname, queryClient]);

  if (!visible) return null;

  return (
    <div
      className={cx(
        "relative z-20 border-b border-cyan-400/25",
        "bg-gradient-to-r from-[#0a1628] via-[#0c1a32] to-[#0a1628]",
        "shadow-[0_8px_32px_rgba(0,0,0,0.45)]"
      )}
      role="status"
      aria-live="polite"
    >
      <div className="max-w-7xl mx-auto px-4 py-2.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <span
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-cyan-400/15 border border-cyan-300/25 text-cyan-200 text-sm font-semibold"
            aria-hidden
          >
            ✦
          </span>
          <p className="text-sm text-white/90">
            <span className="font-semibold text-white">New trends for you</span>
            <span className="text-white/65">
              {" "}
              — {newCount === 1 ? "1 new signal" : `${newCount} new signals`} since you last checked
            </span>
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Link
            to="/"
            onClick={onOpenFeed}
            className="h-9 px-4 rounded-xl text-sm font-semibold bg-white text-slate-900 hover:bg-white/95 transition-colors inline-flex items-center"
          >
            Show
          </Link>
          <button
            type="button"
            onClick={onDismiss}
            className="h-9 w-9 rounded-xl text-white/60 hover:text-white hover:bg-white/10 flex items-center justify-center text-lg leading-none"
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      </div>
    </div>
  );
}
