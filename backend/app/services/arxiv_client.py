"""arXiv data source - research paper abstracts."""
from datetime import datetime, timezone
import re

import httpx

ARXIV_API = "http://export.arxiv.org/api/query"


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class ArxivClient:
    """Fetch recent arXiv abstracts for cs.*, stat.ML, etc."""

    DEFAULT_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "stat.ML"]

    def __init__(self, categories: list[str] | None = None, max_results: int = 200):
        self.categories = categories or self.DEFAULT_CATEGORIES
        self.max_results = max_results

    def fetch_abstracts(self) -> list[dict]:
        """Query arXiv API and return normalized list of abstract entries."""
        out = []
        search_query = " OR ".join(f"cat:{c}" for c in self.categories)
        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.get(ARXIV_API, params=params)
                r.raise_for_status()
                text = r.text
        except Exception:
            return out

        # Parse Atom XML (simple extraction)
        import xml.etree.ElementTree as ET
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return out
        for entry in root.findall(".//atom:entry", ns):
            try:
                title_el = entry.find("atom:title", ns)
                summary_el = entry.find("atom:summary", ns)
                id_el = entry.find("atom:id", ns)
                published_el = entry.find("atom:published", ns)
                title = (title_el.text or "").strip().replace("\n", " ")
                summary = (summary_el.text or "").strip().replace("\n", " ")
                url = id_el.text.strip() if id_el is not None and id_el.text else ""
                arxiv_id = url.split("/")[-1] if url else ""
                if not title and not summary:
                    continue
                text = clean_text(title + " " + summary)
                if not text:
                    continue
                published = published_el.text if published_el is not None and published_el.text else ""
                try:
                    created = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except Exception:
                    created = datetime.now(timezone.utc)
                cats = []
                for c in entry.findall(".//{http://arxiv.org/schemas/atom}primary_category"):
                    if c.get("term"):
                        cats.append(c.get("term"))
                out.append({
                    "source": "arxiv",
                    "external_id": arxiv_id or f"arxiv_{hash(url) % 10**10}",
                    "url": url,
                    "title": title[:2000],
                    "body": text[:50000],
                    "author": None,
                    "created_at": created,
                    "metadata": {"categories": cats} if cats else {},
                })
            except Exception:
                continue
        return out
