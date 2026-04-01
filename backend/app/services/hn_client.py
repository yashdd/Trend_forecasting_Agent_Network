"""Hacker News data source via public API."""
from datetime import datetime, timezone
import re

import httpx

HN_BASE = "https://hacker-news.firebaseio.com/v0"


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class HNClient:
    """Fetch top/ask stories and their top-level comments from HN."""

    def __init__(self, max_stories: int = 100, max_comments_per_story: int = 20):
        self.max_stories = max_stories
        self.max_comments_per_story = max_comments_per_story

    def _fetch_json(self, path: str) -> dict | list:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{HN_BASE}/{path}")
            r.raise_for_status()
            return r.json()

    def fetch_stories(self) -> list[dict]:
        """Fetch top story IDs then story + top comments. Returns normalized list of items."""
        out = []
        try:
            top_ids = self._fetch_json("topstories.json")
        except Exception:
            return out
        ids = (top_ids or [])[: self.max_stories]
        for item_id in ids:
            try:
                item = self._fetch_json(f"item/{item_id}.json")
                if not item or item.get("type") != "story":
                    continue
                title = item.get("title") or ""
                url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
                created = datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc)
                text = clean_text(title + " " + (item.get("text") or ""))
                if not text:
                    text = title
                if not text:
                    continue
                out.append({
                    "source": "hackernews",
                    "external_id": str(item_id),
                    "url": url,
                    "title": title[:2000],
                    "body": text[:50000],
                    "author": item.get("by"),
                    "created_at": created,
                    "metadata": {"hn_id": item_id, "score": item.get("score")},
                })
                # Optionally add top comments as separate "discussions"
                kids = item.get("kids") or []
                for kid_id in kids[: self.max_comments_per_story]:
                    try:
                        kid = self._fetch_json(f"item/{kid_id}.json")
                        if not kid or kid.get("type") != "comment":
                            continue
                        body = clean_text(kid.get("text"))
                        if not body:
                            continue
                        out.append({
                            "source": "hackernews",
                            "external_id": f"comment_{kid_id}",
                            "url": f"https://news.ycombinator.com/item?id={kid_id}",
                            "title": title[:500] + " (comment)",
                            "body": body[:50000],
                            "author": kid.get("by"),
                            "created_at": datetime.fromtimestamp(kid.get("time", 0), tz=timezone.utc),
                            "metadata": {"hn_id": kid_id, "parent": item_id},
                        })
                    except Exception:
                        continue
            except Exception:
                continue
        return out
