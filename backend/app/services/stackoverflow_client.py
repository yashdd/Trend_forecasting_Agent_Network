"""Stack Overflow data source — recent questions on trending tech tags."""
import re
from datetime import datetime, timezone

import httpx

SO_API = "https://api.stackexchange.com/2.3"

TECH_TAGS = [
    "machine-learning", "artificial-intelligence", "deep-learning",
    "large-language-models", "langchain", "openai-api",
    "rust", "webassembly", "kubernetes", "docker",
    "react", "nextjs", "svelte",
]


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class StackOverflowClient:
    """Fetch recent questions from Stack Overflow for tech-related tags."""

    def __init__(self, tags: list[str] | None = None, max_per_tag: int = 30):
        self.tags = tags or TECH_TAGS
        self.max_per_tag = max_per_tag

    def fetch_questions(self) -> list[dict]:
        out: list[dict] = []
        for tag in self.tags:
            params = {
                "order": "desc",
                "sort": "creation",
                "tagged": tag,
                "site": "stackoverflow",
                "filter": "withbody",
                "pagesize": min(self.max_per_tag, 100),
            }
            try:
                with httpx.Client(timeout=30.0) as client:
                    r = client.get(f"{SO_API}/questions", params=params)
                    r.raise_for_status()
                    data = r.json()
            except Exception:
                continue

            for q in data.get("items", []):
                title = q.get("title", "")
                body = q.get("body", "")
                text = clean_text(f"{title} {body}")
                if not text:
                    continue
                try:
                    created = datetime.fromtimestamp(q.get("creation_date", 0), tz=timezone.utc)
                except Exception:
                    created = datetime.now(timezone.utc)
                out.append({
                    "source": "stackoverflow",
                    "external_id": str(q.get("question_id", "")),
                    "url": q.get("link", ""),
                    "title": title[:2000],
                    "body": text,
                    "author": q.get("owner", {}).get("display_name"),
                    "created_at": created,
                    "metadata": {
                        "tags": q.get("tags", []),
                        "score": q.get("score", 0),
                        "answer_count": q.get("answer_count", 0),
                        "view_count": q.get("view_count", 0),
                    },
                })
        return out
