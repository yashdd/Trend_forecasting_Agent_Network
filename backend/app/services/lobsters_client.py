"""Lobste.rs data source — curated tech discussion community."""
import re
from datetime import datetime, timezone

import httpx

LOBSTERS_BASE = "https://lobste.rs"


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class LobstersClient:
    """Fetch hottest and newest stories from Lobste.rs (no auth)."""

    def __init__(self, max_pages: int = 3):
        self.max_pages = max_pages

    def fetch_stories(self) -> list[dict]:
        out: list[dict] = []
        seen_ids: set[str] = set()
        for endpoint in ["hottest", "newest"]:
            for page in range(1, self.max_pages + 1):
                try:
                    with httpx.Client(timeout=30.0) as client:
                        r = client.get(f"{LOBSTERS_BASE}/{endpoint}.json", params={"page": page})
                        r.raise_for_status()
                        stories = r.json()
                except Exception:
                    break
                if not stories:
                    break
                for story in stories:
                    sid = story.get("short_id", "")
                    if sid in seen_ids:
                        continue
                    seen_ids.add(sid)
                    title = story.get("title", "")
                    desc = story.get("description", "")
                    text = clean_text(f"{title} {desc}")
                    if not text:
                        continue
                    try:
                        created = datetime.fromisoformat(story["created_at"].replace("Z", "+00:00"))
                    except Exception:
                        created = datetime.now(timezone.utc)
                    out.append({
                        "source": "lobsters",
                        "external_id": sid,
                        "url": story.get("url") or story.get("comments_url", ""),
                        "title": title[:2000],
                        "body": text,
                        "author": story.get("submitter_user", {}).get("username") if isinstance(story.get("submitter_user"), dict) else story.get("submitter_user"),
                        "created_at": created,
                        "metadata": {
                            "tags": story.get("tags", []),
                            "score": story.get("score", 0),
                            "comment_count": story.get("comment_count", 0),
                        },
                    })
        return out
