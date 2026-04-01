"""Dev.to data source — developer blog posts and community articles."""
import re
from datetime import datetime, timezone

import httpx

DEVTO_API = "https://dev.to/api"


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class DevToClient:
    """Fetch top recent articles from Dev.to (no auth required)."""

    def __init__(self, max_articles: int = 100):
        self.max_articles = min(max_articles, 1000)

    def fetch_articles(self) -> list[dict]:
        out: list[dict] = []
        params = {
            "per_page": min(self.max_articles, 100),
            "top": 7,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(f"{DEVTO_API}/articles", params=params)
                r.raise_for_status()
                articles = r.json()
        except Exception:
            return out

        for art in articles:
            title = art.get("title", "")
            desc = art.get("description", "")
            tags = art.get("tag_list") or []
            text = clean_text(f"{title} {desc} {' '.join(tags)}")
            if not text:
                continue
            try:
                created = datetime.fromisoformat(art["published_at"].replace("Z", "+00:00"))
            except Exception:
                created = datetime.now(timezone.utc)
            out.append({
                "source": "devto",
                "external_id": str(art.get("id", "")),
                "url": art.get("url", ""),
                "title": title[:2000],
                "body": text,
                "author": art.get("user", {}).get("username"),
                "created_at": created,
                "metadata": {
                    "tags": tags,
                    "reactions": art.get("positive_reactions_count", 0),
                    "comments": art.get("comments_count", 0),
                },
            })
        return out
