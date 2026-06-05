"""
IndexScheduler — wraps APScheduler to run the AutoIndexer cycle on a fixed interval.

Lifecycle:
  start()  — called from FastAPI lifespan on startup
  stop()   — called from FastAPI lifespan on shutdown

The scheduler runs in the background using APScheduler's AsyncIOScheduler,
which shares the same event loop as FastAPI so no extra threads are needed.

On startup it also fires the first cycle immediately (next_run_time=now) so
the knowledge base is up-to-date from the moment the server starts, without
waiting for the first interval to elapse.
"""

from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.auto_indexer import AutoIndexer

logger = get_logger(__name__)

_JOB_ID = "auto_index_cycle"


class IndexScheduler:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._indexer = AutoIndexer(settings)
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        if not self._settings.scheduler_enabled:
            logger.info("scheduler_disabled_skipping_start")
            return

        interval_hours = self._settings.scheduler_interval_hours
        logger.info("scheduler_starting", interval_hours=interval_hours)

        self._scheduler.add_job(
            self._run,
            trigger=IntervalTrigger(hours=interval_hours),
            id=_JOB_ID,
            replace_existing=True,
            # Fire immediately on startup, then every N hours after that
            next_run_time=datetime.now(timezone.utc),
        )
        self._scheduler.start()
        logger.info("scheduler_started", interval_hours=interval_hours)

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")

    async def _run(self) -> None:
        """Wrapper so APScheduler exceptions are logged, not silently swallowed."""
        try:
            await self._indexer.run_cycle()
        except Exception as exc:
            logger.error("scheduler_job_failed", error=str(exc), exc_info=True)
