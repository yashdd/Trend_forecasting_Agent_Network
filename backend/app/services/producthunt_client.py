"""Product Hunt data source — recent product launches."""
import re
from datetime import datetime, timezone

import httpx

from app.config import get_settings

PH_API = "https://api.producthunt.com/v2/api/graphql"

POSTS_QUERY = """
query {
  posts(order: VOTES, first: 50) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        createdAt
        makers { username }
        topics { edges { node { name } } }
      }
    }
  }
}
"""


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class ProductHuntClient:
    """Fetch top recent launches from Product Hunt GraphQL API."""

    def fetch_posts(self) -> list[dict]:
        out: list[dict] = []
        settings = get_settings()
        token = getattr(settings, "producthunt_api_token", "") or ""
        if not token:
            return out
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(PH_API, json={"query": POSTS_QUERY}, headers=headers)
                r.raise_for_status()
                data = r.json()
        except Exception:
            return out

        edges = (data.get("data") or {}).get("posts", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            name = node.get("name", "")
            tagline = node.get("tagline", "")
            desc = node.get("description", "")
            text = clean_text(f"{name} {tagline} {desc}")
            if not text:
                continue
            try:
                created = datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00"))
            except Exception:
                created = datetime.now(timezone.utc)
            makers = [m.get("username") for m in (node.get("makers") or [])]
            topic_names = [
                t["node"]["name"]
                for t in (node.get("topics", {}).get("edges") or [])
                if t.get("node")
            ]
            out.append({
                "source": "producthunt",
                "external_id": str(node.get("id", "")),
                "url": node.get("url", ""),
                "title": f"{name}: {tagline}"[:2000],
                "body": text,
                "author": makers[0] if makers else None,
                "created_at": created,
                "metadata": {
                    "votes": node.get("votesCount", 0),
                    "topics": topic_names,
                    "makers": makers,
                },
            })
        return out
