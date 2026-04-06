"""Google Trends data source — search interest spikes for tech keywords."""
import re
from datetime import datetime, timezone
from hashlib import sha256

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None


TECH_KEYWORDS_POOL = [
    "AI agent", "LLM", "RAG", "vector database", "rust programming",
    "web3", "edge computing", "quantum computing", "RISC-V", "WebAssembly",
    "MLOps", "fine tuning LLM", "diffusion model", "robotics AI",
    "autonomous driving", "cybersecurity AI", "digital twin", "AR VR",
    "generative AI", "open source AI",
]


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


class GoogleTrendsClient:
    """
    Check Google Trends for rising interest in curated tech keywords.

    Only keywords with meaningful interest are returned as "posts".
    Rate-limited; batches of 5 keywords at a time (Google's limit).
    """

    def __init__(self, keywords: list[str] | None = None):
        self.keywords = keywords or TECH_KEYWORDS_POOL

    def fetch_trends(self) -> list[dict]:
        if TrendReq is None:
            return []
        out: list[dict] = []
        try:
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 30))
        except Exception:
            return out

        batches = [self.keywords[i:i + 5] for i in range(0, len(self.keywords), 5)]
        for batch in batches:
            try:
                pytrends.build_payload(batch, cat=0, timeframe="now 7-d")
                interest = pytrends.interest_over_time()
                if interest is None or interest.empty:
                    continue
                for kw in batch:
                    if kw not in interest.columns:
                        continue
                    series = interest[kw]
                    mean_interest = float(series.mean())
                    latest = float(series.iloc[-1]) if len(series) > 0 else 0
                    if mean_interest < 10:
                        continue
                    ext_id = sha256(kw.encode()).hexdigest()[:16]
                    text = clean_text(f"Google Trends: '{kw}' — average interest {mean_interest:.0f}/100, latest {latest:.0f}/100 over the past 7 days.")
                    out.append({
                        "source": "google_trends",
                        "external_id": ext_id,
                        "url": f"https://trends.google.com/trends/explore?q={kw.replace(' ', '+')}",
                        "title": f"Google Trends: {kw}"[:2000],
                        "body": text,
                        "author": None,
                        "created_at": datetime.now(timezone.utc),
                        "metadata": {
                            "keyword": kw,
                            "mean_interest": round(mean_interest, 2),
                            "latest_interest": latest,
                        },
                    })
            except Exception:
                continue
        return out
