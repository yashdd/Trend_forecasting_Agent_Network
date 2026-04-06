"""Embedding & Topic Clustering Agent: embed text, run BERTopic/HDBSCAN, store assignments."""
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.orm import RawPost, Embedding, Topic, TopicAssignment, EMBEDDING_DIM
from app.services.embedding_service import (
    get_embedding_model,
    embed_texts,
    build_topic_model,
    fit_topic_model,
)
from app.agents.state import TrendPipelineState
from app.config import get_settings


def run_embedding_clustering(state: TrendPipelineState) -> TrendPipelineState:
    """
    - Load raw_posts that don't have embeddings; embed and store.
    - Load all raw_posts with embeddings; fit BERTopic; create/update topics and assignments.
    """
    session = get_sync_session()
    try:
        settings = get_settings()
        batch_size = getattr(settings, "pipeline_batch_size_embed", 64)

        # 1) Embed posts that don't have an embedding
        subq = select(Embedding.raw_post_id)
        no_emb = session.execute(
            select(RawPost).where(RawPost.id.not_in(subq))
        ).scalars().all()
        new_emb_count = 0
        if no_emb:
            model = get_embedding_model()
            texts = [r.body or r.title or "" for r in no_emb]
            if any(t.strip() for t in texts):
                arr = embed_texts(model, texts, batch_size=batch_size)
                now = datetime.now(timezone.utc)
                for row, vec in zip(no_emb, arr):
                    emb = Embedding(
                        raw_post_id=row.id,
                        embedding=vec.tolist(),
                        model_name=settings.embedding_model_name,
                        created_at=now,
                    )
                    session.add(emb)
                    new_emb_count += 1
            session.flush()

        # 2) All posts that have embeddings (for clustering)
        with_emb = session.execute(
            select(RawPost, Embedding)
            .join(Embedding, RawPost.id == Embedding.raw_post_id)
        ).all()
        if not with_emb:
            return {
                **state,
                "new_embeddings_created": 0,
                "clustered_post_count": 0,
                "topic_assignment_count": 0,
            }

        raw_ids = [r.id for r, _ in with_emb]
        texts = [r.body or r.title or "" for r, _ in with_emb]
        embeddings = np.array([e.embedding for _, e in with_emb])

        # 3) Fit BERTopic
        topic_model = build_topic_model(EMBEDDING_DIM)
        topic_ids, topic_labels_list, topic_info = fit_topic_model(topic_model, texts, embeddings)

        # 4) Build centroids for each BERTopic cluster (for continuity)
        cluster_vecs: dict[int, np.ndarray] = {}
        counts: dict[int, int] = {}
        for bt_id, vec in zip(topic_ids, embeddings):
            if bt_id is None:
                continue
            if bt_id not in cluster_vecs:
                cluster_vecs[bt_id] = np.array(vec, dtype=np.float32)
                counts[bt_id] = 1
            else:
                cluster_vecs[bt_id] += np.array(vec, dtype=np.float32)
                counts[bt_id] += 1
        for bt_id in list(cluster_vecs.keys()):
            cluster_vecs[bt_id] = cluster_vecs[bt_id] / float(counts.get(bt_id, 1))

        # Load existing topic centroids
        existing_topics = session.execute(select(Topic).where(Topic.embedding.isnot(None))).scalars().all()
        existing_ids = [t.id for t in existing_topics]
        existing_centroids = np.array([np.array(t.embedding, dtype=np.float32) for t in existing_topics]) if existing_topics else None
        if existing_centroids is not None and len(existing_centroids) > 0:
            norms = np.linalg.norm(existing_centroids, axis=1) + 1e-9
            existing_centroids = existing_centroids / norms[:, None]

        def match_existing(vec: np.ndarray, threshold: float = 0.86) -> int | None:
            if existing_centroids is None or len(existing_centroids) == 0:
                return None
            v = vec.astype(np.float32)
            v = v / (np.linalg.norm(v) + 1e-9)
            sims = existing_centroids @ v
            best_idx = int(np.argmax(sims))
            if float(sims[best_idx]) >= threshold:
                return int(existing_ids[best_idx])
            return None

        # 5) Get or create Topic rows; map BERTopic index -> our topic id
        bt_index_to_topic_id: dict[int, int] = {}
        now = datetime.now(timezone.utc)
        for info in topic_info or []:
            tid = info.get("Topic")
            if tid is None or tid == -1:
                continue
            label = (info.get("Name") or f"topic_{tid}").strip()
            if not label:
                continue
            centroid = cluster_vecs.get(tid)
            matched_id = match_existing(centroid) if centroid is not None else None
            if matched_id is not None:
                topic = session.execute(select(Topic).where(Topic.id == matched_id)).scalars().first()
                if topic:
                    topic.label = label
                    topic.keywords = label.replace("_", " ").split()[:15]
                    topic.updated_at = now
                    topic.embedding = centroid.tolist() if centroid is not None else topic.embedding
                    bt_index_to_topic_id[tid] = topic.id
                    continue

            existing = session.execute(select(Topic).where(Topic.label == label)).scalars().first()
            if existing:
                existing.updated_at = now
                if centroid is not None:
                    existing.embedding = centroid.tolist()
                bt_index_to_topic_id[tid] = existing.id
                continue

            topic = Topic(
                label=label,
                keywords=label.replace("_", " ").split()[:15],
                embedding=centroid.tolist() if centroid is not None else None,
                first_seen_at=now,
                updated_at=now,
            )
            session.add(topic)
            session.flush()
            bt_index_to_topic_id[tid] = topic.id

        if -1 in set(topic_ids) and -1 not in bt_index_to_topic_id:
            existing = session.execute(select(Topic).where(Topic.label == "Outlier")).scalars().first()
            if existing:
                bt_index_to_topic_id[-1] = existing.id
            else:
                outlier = Topic(label="Outlier", keywords=["outlier"], first_seen_at=now, updated_at=now)
                session.add(outlier)
                session.flush()
                bt_index_to_topic_id[-1] = outlier.id

        # 6) Delete existing assignments for these raw_posts, then insert new ones
        session.execute(TopicAssignment.__table__.delete().where(TopicAssignment.raw_post_id.in_(raw_ids)))
        session.flush()

        # 7) Insert topic_assignments (full mapping only in DB; state keeps count)
        assignment_count = 0
        for raw_post_id, bt_id in zip(raw_ids, topic_ids):
            our_topic_id = bt_index_to_topic_id.get(bt_id)
            if our_topic_id is None:
                continue
            session.add(
                TopicAssignment(
                    raw_post_id=raw_post_id,
                    topic_id=our_topic_id,
                    assigned_at=now,
                )
            )
            assignment_count += 1

        session.commit()

        return {
            **state,
            "new_embeddings_created": new_emb_count,
            "clustered_post_count": len(raw_ids),
            "topic_assignment_count": assignment_count,
        }
    except Exception as e:
        session.rollback()
        return {**state, "error": str(e)}
    finally:
        session.close()
