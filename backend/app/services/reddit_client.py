"""Reddit data source via PRAW."""
import re
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

# Optional: PRAW only loaded if credentials exist
try:
    import praw
except ImportError:
    praw = None


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class RedditClient:
    """Fetch posts and comments from configured subreddits."""

    DEFAULT_SUBREDDITS = ["technology", "startups", "MachineLearning", "artificial", "programming"]

    def __init__(self, subreddits: list[str] | None = None):
        self.subreddits = subreddits or self.DEFAULT_SUBREDDITS
        self._reddit = None

    def _get_reddit(self) -> Any:
        if praw is None:
            raise RuntimeError("praw is not installed")
        settings = get_settings()
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            raise ValueError("Reddit credentials not configured")
        if self._reddit is None:
            self._reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
        return self._reddit

    def fetch_posts(self, limit_per_sub: int = 50) -> list[dict]:
        """Fetch recent hot/new posts from each subreddit. Returns list of normalized dicts."""
        out = []
        try:
            reddit = self._get_reddit()
        except (ValueError, RuntimeError):
            return out
        for sub in self.subreddits:
            try:
                subreddit = reddit.subreddit(sub)
                for post in subreddit.hot(limit=limit_per_sub):
                    created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                    text = clean_text((post.title or "") + " " + (post.selftext or ""))
                    if not text:
                        continue
                    out.append({
                        "source": "reddit",
                        "external_id": post.id,
                        "url": f"https://reddit.com{post.permalink}",
                        "title": (post.title or "")[:2000],
                        "body": text[:50000],
                        "author": getattr(post.author, "name", None) if post.author else None,
                        "created_at": created,
                        "metadata": {"subreddit": sub},
                    })
            except Exception:
                continue
        return out
