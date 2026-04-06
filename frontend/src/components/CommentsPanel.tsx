import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchSignalComments, postSignalComment } from "../api/client";
import { Button, cx } from "./ui";

export default function CommentsPanel(props: { signalId: number }) {
  const qc = useQueryClient();
  const [beforeId, setBeforeId] = useState<number | null>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ["comments", props.signalId, beforeId],
    queryFn: () => fetchSignalComments(props.signalId, { limit: 50, before_id: beforeId }),
  });

  const viewerLabel = data?.viewer_label ?? "Anonymous";
  const pageComments = data?.comments ?? [];
  const hasMore = data?.has_more ?? false;
  const nextBeforeId = data?.next_before_id ?? null;

  const [text, setText] = useState("");
  const trimmed = useMemo(() => text.trim(), [text]);

  const post = useMutation({
    mutationFn: async () => postSignalComment(props.signalId, { body: trimmed }),
    onSuccess: async () => {
      setText("");
      setBeforeId(null);
      await qc.invalidateQueries({ queryKey: ["comments", props.signalId] });
    },
  });
  const postError = post.error instanceof Error ? post.error.message : post.error ? String(post.error) : null;

  return (
    <div className="mt-4 rounded-2xl border border-white/10 bg-white/4 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm text-white/80 font-medium">Comments</p>
        <p className="text-xs text-white/55">You’re posting as <span className="text-white/80">{viewerLabel}</span></p>
      </div>

      <div className="mt-3 space-y-3">
        {isLoading ? <p className="text-sm text-white/55">Loading comments…</p> : null}
        {error ? <p className="text-sm text-rose-300">{(error as Error).message}</p> : null}

        {!isLoading && pageComments.length === 0 ? (
          <p className="text-sm text-white/55">No comments yet. Start the discussion.</p>
        ) : null}

        {hasMore ? (
          <div className="flex justify-center">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setBeforeId(nextBeforeId)}
              disabled={!nextBeforeId}
            >
              Load older
            </Button>
          </div>
        ) : null}

        {pageComments.map((c) => (
          <div key={c.id} className="rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-white/65 font-medium">{c.author_label}</span>
              <span className="text-xs text-white/40">
                {c.created_at ? new Date(c.created_at).toLocaleString() : ""}
              </span>
            </div>
            <p className="mt-2 text-sm text-white/85 whitespace-pre-wrap">{c.body}</p>
          </div>
        ))}
      </div>

      <div className="mt-4">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="Write a comment…"
          className={cx(
            "w-full resize-none rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white/90 placeholder:text-white/40",
            "focus:outline-none focus:ring-2 focus:ring-cyan-400/30 focus:border-cyan-300/30"
          )}
        />
        <div className="mt-2 flex items-center justify-between gap-3">
          <p className="text-xs text-white/45">Anonymous. No login. Keep it respectful.</p>
          <Button
            type="button"
            size="sm"
            onClick={() => post.mutate()}
            disabled={post.isPending || trimmed.length === 0 || trimmed.length > 2000}
          >
            {post.isPending ? "Posting…" : "Post"}
          </Button>
        </div>
        {trimmed.length > 2000 ? <p className="text-xs text-rose-300 mt-2">Max 2000 characters.</p> : null}
        {postError ? (
          <p className="text-xs text-rose-300 mt-2" role="alert">
            {postError}
          </p>
        ) : null}
      </div>
    </div>
  );
}

