"""Databricks Jobs client for optional external pipeline scheduling."""
import httpx

from app.config import get_settings


def trigger_databricks_pipeline_job() -> dict:
    """
    Trigger configured Databricks Job via Jobs API run-now.

    Returns a small status dict for logging/observability.
    """
    settings = get_settings()
    host = (settings.databricks_host or "").rstrip("/")
    token = settings.databricks_token or ""
    job_id = settings.databricks_pipeline_job_id
    if not settings.use_databricks_jobs:
        return {"status": "disabled", "message": "Databricks mode is disabled."}
    if not host or not token or not job_id:
        return {"status": "skipped", "message": "Missing Databricks host/token/job_id."}

    url = f"{host}/api/2.1/jobs/run-now"
    payload = {"job_id": int(job_id)}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        return {
            "status": "accepted",
            "run_id": data.get("run_id"),
            "number_in_job": data.get("number_in_job"),
        }
    except Exception as exc:
        return {"status": "failed", "message": str(exc)}

