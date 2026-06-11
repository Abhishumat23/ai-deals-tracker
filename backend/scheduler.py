"""
Scheduler: runs all scraper checks on a fixed interval using APScheduler.
Designed to run inside the FastAPI process (same event loop).

- Default: every 60 minutes
- Configurable via SCRAPE_INTERVAL_MINUTES env var
- Failures in one scraper never crash the scheduler
"""

import asyncio
import logging
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import get_db_session
from scrapers import ALL_SCRAPERS
from detector import process_scrape_result
from notifier import send_alert

logger = logging.getLogger(__name__)

# How often to run checks (default: 60 minutes)
INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))


async def run_single_scraper(tool_name: str, scrape_fn) -> None:
    """
    Run one scraper, detect changes, and send alerts if needed.
    All exceptions are caught so one failure doesn't affect others.
    """
    logger.info(f"[Scheduler] Running scraper for {tool_name}")
    try:
        # Run the async scraper
        data = await scrape_fn()

        if data is None:
            logger.warning(f"[Scheduler] {tool_name} scraper returned None — skipping")
            return

        # Detect changes and write to DB
        with get_db_session() as db:
            change = process_scrape_result(db, tool_name, data)

        # Send Telegram alert if change was detected
        if change:
            await send_alert(change)

    except Exception as e:
        logger.error(f"[Scheduler] Unexpected error for {tool_name}: {e}", exc_info=True)


async def run_all_scrapers() -> dict:
    """
    Run all registered scrapers with limited concurrency to avoid CPU overload.
    Returns a summary dict for the manual /run-check endpoint.
    """
    logger.info(f"[Scheduler] Starting check for {len(ALL_SCRAPERS)} tools")

    sem = asyncio.Semaphore(2)

    async def run_with_sem(tool_name, scrape_fn):
        async with sem:
            return await run_single_scraper(tool_name, scrape_fn)

    tasks = [
        run_with_sem(tool_name, scrape_fn)
        for tool_name, scrape_fn in ALL_SCRAPERS
    ]

    # Run all scrapers; gather so we get all results
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summary = {
        "tools_checked": len(ALL_SCRAPERS),
        "errors": sum(1 for r in results if isinstance(r, Exception)),
    }
    logger.info(f"[Scheduler] Check complete: {summary}")
    return summary


def create_scheduler() -> AsyncIOScheduler:
    """
    Build and return a configured APScheduler instance.
    Call scheduler.start() in the FastAPI lifespan.
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        run_all_scrapers,
        trigger=IntervalTrigger(minutes=INTERVAL_MINUTES),
        id="scrape_all",
        name="Scrape all AI pricing pages",
        replace_existing=True,
        max_instances=1,          # prevent overlapping runs
        coalesce=True,            # skip missed runs instead of backfilling
    )

    logger.info(f"[Scheduler] Configured — interval={INTERVAL_MINUTES}min")
    return scheduler
