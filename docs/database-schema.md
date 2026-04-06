# Database Schema

PostgreSQL with the pgvector extension. All timestamps in UTC.

## Tables

### sources

| Column   | Type         | Description                    |
|----------|--------------|--------------------------------|
| id       | SERIAL       | PK                             |
| name     | VARCHAR(64)  | reddit, hackernews, arxiv      |
| config   | JSONB        | e.g. subreddits, categories    |

### raw_posts

| Column      | Type            | Description        |
|-------------|-----------------|--------------------|
| id          | SERIAL          | PK                 |
| source_id   | INT             | FK → sources       |
| external_id | VARCHAR(256)    | Unique per source  |
| url         | TEXT            |                    |
| title       | TEXT            |                    |
| body        | TEXT            |                    |
| author      | VARCHAR(256)    |                    |
| created_at  | TIMESTAMPTZ     | Original post time |
| fetched_at  | TIMESTAMPTZ     | When we stored it  |
| metadata    | JSONB           |                    |

Unique: `(source_id, external_id)`.

### embeddings

| Column      | Type         | Description   |
|-------------|--------------|---------------|
| id          | SERIAL       | PK            |
| raw_post_id | INT          | FK → raw_posts, ON DELETE CASCADE |
| embedding   | VECTOR(384)  | all-MiniLM-L6-v2 |
| model_name  | VARCHAR(128) |               |
| created_at  | TIMESTAMPTZ  |               |

Index: HNSW on `embedding` for cosine similarity.

### topics

| Column        | Type          | Description   |
|---------------|---------------|---------------|
| id            | SERIAL        | PK            |
| label         | VARCHAR(512)  | From BERTopic |
| keywords      | JSONB         |               |
| embedding     | VECTOR(384)   | Optional centroid |
| first_seen_at | TIMESTAMPTZ   |               |
| updated_at    | TIMESTAMPTZ   |               |

### topic_assignments

| Column      | Type         |
|-------------|--------------|
| id          | SERIAL       | PK |
| raw_post_id | INT          | FK → raw_posts |
| topic_id    | INT          | FK → topics |
| score       | FLOAT        | Optional |
| assigned_at | TIMESTAMPTZ  | |

### topic_daily_metrics

| Column          | Type    |
|-----------------|---------|
| id              | SERIAL  | PK |
| topic_id        | INT     | FK → topics |
| date            | DATE    | |
| mention_count   | INT     | |
| growth_rate     | FLOAT   | |
| acceleration    | FLOAT   | |
| signal_score    | FLOAT   | |
| source_breakdown| JSONB   | e.g. {"reddit": 5, "hackernews": 2} |

Unique: `(topic_id, date)`.

### cross_source_validation

| Column                | Type         |
|------------------------|--------------|
| id                     | SERIAL       | PK |
| topic_id               | INT          | FK → topics |
| date                   | DATE         | |
| sources_present        | JSONB        | Array of source names |
| cross_source_strength  | FLOAT        | 0–1 |
| validated_at           | TIMESTAMPTZ  | |

Unique: `(topic_id, date)`.

### trend_insights

| Column                 | Type         |
|------------------------|--------------|
| id                     | SERIAL       | PK |
| topic_id               | INT          | FK → topics |
| generated_at           | TIMESTAMPTZ  | |
| summary                | TEXT         | |
| why_it_matters         | TEXT         | |
| industry_impact        | TEXT         | |
| representative_sources | JSONB        | |
| llm_metadata           | JSONB        | |

### weekly_reports

| Column          | Type         |
|-----------------|--------------|
| id              | SERIAL       | PK |
| period_start    | DATE         | |
| period_end      | DATE         | |
| top_signals     | JSONB        | |
| report_markdown | TEXT         | |
| created_at      | TIMESTAMPTZ  | |

### pipeline_runs

| Column        | Type         |
|---------------|--------------|
| id            | SERIAL       | PK |
| started_at    | TIMESTAMPTZ  | |
| finished_at   | TIMESTAMPTZ  | |
| status        | VARCHAR(32)  | running, success, failed |
| agent_steps   | JSONB        | |
| error_message | TEXT         | |
