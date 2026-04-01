"""Scheduled jobs."""
from app.jobs.pipeline_job import run_daily_pipeline

__all__ = ["run_daily_pipeline"]
