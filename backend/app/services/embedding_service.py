"""Sentence embedding and BERTopic clustering."""
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP

from app.config import get_settings
from app.models.orm import EMBEDDING_DIM


def get_embedding_model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model_name)


def embed_texts(model: SentenceTransformer, texts: list[str], batch_size: int = 64) -> np.ndarray:
    return model.encode(texts, batch_size=batch_size, show_progress_bar=False)


def build_topic_model(embedding_dim: int = EMBEDDING_DIM):
    """BERTopic with HDBSCAN on precomputed embeddings (no UMAP inside BERTopic)."""
    hdbscan = HDBSCAN(
        min_cluster_size=5,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    # We pass embeddings from our model; BERTopic can use them via fit_transform(docs, embeddings)
    return BERTopic(
        embedding_model=None,
        hdbscan_model=hdbscan,
        umap_model=UMAP(n_components=5, metric="cosine", random_state=42),
        verbose=False,
    )


def fit_topic_model(
    topic_model: BERTopic,
    texts: list[str],
    embeddings: np.ndarray,
) -> tuple[list[int], list[str | None], list[dict]]:
    """Fit BERTopic on (texts, embeddings). Returns topic_ids, topic_labels, topic_info."""
    topic_ids, _ = topic_model.fit_transform(texts, embeddings=embeddings)
    labels = topic_model.topic_labels_ or {}
    # topic_ids: -1 is outlier; 0, 1, ... are topic indices
    topic_labels_list = [labels.get(tid, None) for tid in (topic_ids or [])]
    return list(topic_ids or []), topic_labels_list, topic_model.get_topic_info().to_dict("records") if hasattr(topic_model, "get_topic_info") else []


def transform_topic_model(
    topic_model: BERTopic,
    embeddings: np.ndarray,
) -> list[int]:
    """Assign new embeddings to existing topics (or -1)."""
    topic_ids, _ = topic_model.transform(None, embeddings)
    return list(topic_ids) if topic_ids is not None else []
