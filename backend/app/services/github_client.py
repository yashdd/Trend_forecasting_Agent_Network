"""GitHub Trending data source — recently popular repositories."""
import re
from datetime import datetime, timezone, timedelta

import httpx

from app.config import get_settings

GITHUB_API = "https://api.github.com"


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class GitHubClient:
    """Fetch recently-created repos gaining stars via the GitHub Search API."""

    def __init__(self, max_results: int = 100):
        self.max_results = min(max_results, 100)

    def _headers(self) -> dict:
        settings = get_settings()
        token = getattr(settings, "github_token", "") or ""
        h = {"Accept": "application/vnd.github+json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def fetch_repos(self) -> list[dict]:
        out: list[dict] = []
        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        params = {
            "q": f"created:>{since} stars:>5",
            "sort": "stars",
            "order": "desc",
            "per_page": self.max_results,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(f"{GITHUB_API}/search/repositories", params=params, headers=self._headers())
                r.raise_for_status()
                data = r.json()
        except Exception:
            return out

        for repo in data.get("items", []):
            name = repo.get("full_name", "")
            desc = repo.get("description") or ""
            text = clean_text(f"{name} {desc}")
            if not text:
                continue
            try:
                created = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
            except Exception:
                created = datetime.now(timezone.utc)
            out.append({
                "source": "github",
                "external_id": str(repo.get("id", "")),
                "url": repo.get("html_url", ""),
                "title": name[:2000],
                "body": text,
                "author": repo.get("owner", {}).get("login"),
                "created_at": created,
                "metadata": {
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "language": repo.get("language"),
                    "topics": repo.get("topics", []),
                },
            })
        return out
