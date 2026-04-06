"""Tech News RSS data source — aggregates multiple tech media feeds."""
import re
from datetime import datetime, timezone
from hashlib import sha256

try:
    import feedparser
except ImportError:
    feedparser = None


DEFAULT_FEEDS = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("VentureBeat", "https://venturebeat.com/feed/"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
]


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class RSSClient:
    """Parse RSS/Atom feeds from major tech news outlets."""

    def __init__(self, feeds: list[tuple[str, str]] | None = None, max_per_feed: int = 30):
        self.feeds = feeds or DEFAULT_FEEDS
        self.max_per_feed = max_per_feed

    def fetch_articles(self) -> list[dict]:
        if feedparser is None:
            return []
        out: list[dict] = []
        for outlet_name, url in self.feeds:
            try:
                feed = feedparser.parse(url)
                entries = feed.get("entries", [])[:self.max_per_feed]
                for entry in entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "") or entry.get("description", "")
                    text = clean_text(f"{title} {summary}")
                    if not text:
                        continue
                    link = entry.get("link", "")
                    ext_id = sha256(link.encode()).hexdigest()[:16] if link else sha256(title.encode()).hexdigest()[:16]
                    published = entry.get("published_parsed") or entry.get("updated_parsed")
                    if published:
                        try:
                            from time import mktime
                            created = datetime.fromtimestamp(mktime(published), tz=timezone.utc)
                        except Exception:
                            created = datetime.now(timezone.utc)
                    else:
                        created = datetime.now(timezone.utc)
                    author = entry.get("author")
                    out.append({
                        "source": "rss_news",
                        "external_id": ext_id,
                        "url": link,
                        "title": title[:2000],
                        "body": text,
                        "author": author,
                        "created_at": created,
                        "metadata": {"outlet": outlet_name},
                    })
            except Exception:
                continue
        return out
