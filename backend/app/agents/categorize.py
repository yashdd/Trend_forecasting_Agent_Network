"""Category Assignment Agent: assign high-level categories to topics."""
from collections import Counter, defaultdict
from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.orm import Topic, TopicAssignment, RawPost, Source
from app.agents.state import TrendPipelineState


CATEGORY_NAMES = [
    "startups",
    "open_source_tools",
    "research_methods",
    "ai_models",
    "developer_platforms",
    "security_privacy",
    "cloud_infra",
    "robotics_hardware",
    "web3_fintech",
    "policy_regulation",
]


def _score_topic(session: Session, topic_id: int) -> Dict[str, float]:
    """Compute simple heuristic scores per category for a topic."""
    rows = session.execute(
        select(RawPost, Source.name)
        .join(TopicAssignment, RawPost.id == TopicAssignment.raw_post_id)
        .join(Source, RawPost.source_id == Source.id)
        .where(TopicAssignment.topic_id == topic_id)
        .limit(200)
    ).all()
    if not rows:
        return {}

    scores: Dict[str, float] = defaultdict(float)
    source_counts: Counter = Counter()

    for post, source_name in rows:
        text = (post.title or "") + " " + (post.body or "")
        low = text.lower()
        source_counts[source_name] += 1

        startup_keywords = [
            "startup", "seed round", "series a", "series b", "series c",
            "funding", "raised", "yc", "y combinator", "acquired",
            "launch", "show hn", "pre-seed", "valuation", "pivot",
            "founder", "co-founder", "incubator", "accelerator",
        ]
        if any(k in low for k in startup_keywords):
            scores["startups"] += 1.0

        research_keywords = [
            "theorem", "corollary", "proof", "lemma", "optimization",
            "convergence", "distribution", "dataset", "benchmark",
            "architecture", "transformer", "attention mechanism",
            "fine-tuning", "pre-training", "reinforcement learning",
            "diffusion", "neural network", "gradient", "loss function",
        ]
        if any(k in low for k in research_keywords):
            scores["research_methods"] += 0.8

        ai_model_keywords = [
            "llm", "large language model", "gpt", "gemini", "claude", "mistral",
            "moe", "context window", "inference", "token", "multimodal", "agentic ai",
            "alignment model", "reasoning model",
        ]
        if any(k in low for k in ai_model_keywords):
            scores["ai_models"] += 0.8

        tools_keywords = [
            "library", "framework", "sdk", "package", "api client",
            "open source", "github.com", "pip install", "npm install",
            "cargo install", "brew install", "cli tool", "devtool",
            "plugin", "extension", "middleware", "docker image",
        ]
        if any(k in low for k in tools_keywords):
            scores["open_source_tools"] += 0.9

        platform_keywords = [
            "api", "platform", "saas", "developer portal", "integration",
            "workflow", "orchestration", "ecosystem", "marketplace", "developer experience",
        ]
        if any(k in low for k in platform_keywords):
            scores["developer_platforms"] += 0.75

        security_keywords = [
            "security", "vulnerability", "cve", "breach", "zero-day", "exploit",
            "privacy", "encryption", "compliance", "gdpr", "hipaa", "data protection",
            "identity", "authentication", "authorization",
        ]
        if any(k in low for k in security_keywords):
            scores["security_privacy"] += 0.85

        cloud_keywords = [
            "kubernetes", "k8s", "container", "serverless", "aws", "azure", "gcp",
            "cloud", "edge", "distributed systems", "infrastructure", "observability",
            "devops", "ci/cd",
        ]
        if any(k in low for k in cloud_keywords):
            scores["cloud_infra"] += 0.85

        hardware_keywords = [
            "robotics", "drone", "autonomous", "embedded", "microcontroller", "sensor",
            "raspberry pi", "arduino", "chip", "gpu", "risc-v", "firmware",
        ]
        if any(k in low for k in hardware_keywords):
            scores["robotics_hardware"] += 0.8

        web3_fintech_keywords = [
            "crypto", "blockchain", "smart contract", "defi", "wallet",
            "payments", "fintech", "banking", "stablecoin", "tokenization",
        ]
        if any(k in low for k in web3_fintech_keywords):
            scores["web3_fintech"] += 0.75

        policy_keywords = [
            "regulator", "regulation", "eu ai act", "policy", "ban", "lawsuit", "antitrust",
            "executive order", "copyright", "responsible ai", "fairness", "governance",
        ]
        if any(k in low for k in policy_keywords):
            scores["policy_regulation"] += 0.9

    # Source-aware boosts
    total_posts = sum(source_counts.values()) or 1

    # Product Hunt is startup-heavy
    ph_ratio = source_counts.get("producthunt", 0) / total_posts
    if ph_ratio > 0.3:
        scores["startups"] += ph_ratio * 2.0

    # GitHub repos are tool-heavy
    gh_ratio = source_counts.get("github", 0) / total_posts
    if gh_ratio > 0.3:
        scores["open_source_tools"] += gh_ratio * 2.0

    # RSS news outlets are news-heavy
    rss_ratio = source_counts.get("rss_news", 0) / total_posts
    if rss_ratio > 0.3:
        scores["developer_platforms"] += rss_ratio * 0.6
        scores["policy_regulation"] += rss_ratio * 0.6

    # arXiv is concept-heavy
    arxiv_ratio = source_counts.get("arxiv", 0) / total_posts
    if arxiv_ratio > 0.3:
        scores["research_methods"] += arxiv_ratio * 2.0
        scores["ai_models"] += arxiv_ratio * 1.0

    # Stack Overflow is tools/concepts
    so_ratio = source_counts.get("stackoverflow", 0) / total_posts
    if so_ratio > 0.3:
        scores["open_source_tools"] += so_ratio * 1.0
        scores["developer_platforms"] += so_ratio * 0.6

    total = sum(scores.values()) or 1.0
    for k in list(scores.keys()):
        scores[k] = round(scores[k] / total, 4)

    return dict(scores)


def run_categorize(state: TrendPipelineState) -> TrendPipelineState:
    """Assign category and scores for each topic based on its posts."""
    session = get_sync_session()
    try:
        topics = session.execute(select(Topic)).scalars().all()
        for topic in topics:
            scores = _score_topic(session, topic.id)
            if not scores:
                continue
            best_cat, best_score = max(scores.items(), key=lambda kv: kv[1])
            # Threshold to avoid noisy assignments.
            if best_score < 0.55:
                continue
            topic.category = best_cat
            topic.category_scores = scores
            topic.category_explanation = f"category={best_cat}, score={best_score}, scores={scores}"
        session.commit()
        return state
    except Exception as e:
        session.rollback()
        return {**state, "error": str(e)}
    finally:
        session.close()

