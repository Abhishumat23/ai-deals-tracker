"""
FastAPI application entry point.

Endpoints:
  GET  /tools       — latest snapshot per tool
  GET  /changes     — recent detected changes
  GET  /latest      — last 5 changes
  POST /run-check   — trigger an immediate scrape cycle
  GET  /health      — heartbeat

Runs the APScheduler inside the same process via lifespan events.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import init_db, get_db
from models import Snapshot, Change
from scheduler import create_scheduler, run_all_scrapers
from notifier import send_startup_message

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB, start scheduler, send startup Telegram ping."""
    global scheduler

    logger.info("=== AI Deals Tracker starting ===")

    # 1. Ensure DB tables exist
    init_db()

    # 2. Start background scheduler
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("[App] Scheduler started")

    # 3. Optional: notify Telegram that the app started
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        await send_startup_message()

    yield  # app is live

    # Shutdown
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[App] Scheduler stopped")
    logger.info("=== AI Deals Tracker stopped ===")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Deals Tracker",
    description="Monitors AI tool pricing pages and alerts on changes.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Next.js frontend (localhost:3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _snapshot_to_dict(s: Snapshot) -> dict:
    import json
    structured = {}
    if s.structured_json:
        try:
            structured = json.loads(s.structured_json)
        except Exception:
            pass
    return {
        "id": s.id,
        "tool_name": s.tool_name,
        "content_hash": s.content_hash,
        "prices_found": structured.get("prices_found", []),
        "tiers": structured.get("tiers", []),
        "created_at": s.created_at.isoformat(),
    }


def _change_to_dict(c: Change) -> dict:
    return {
        "id": c.id,
        "tool_name": c.tool_name,
        "summary": c.summary,
        "detected_at": c.detected_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """Simple heartbeat endpoint."""
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@app.get("/tools")
def get_tools(db: Session = Depends(get_db)):
    """
    Return the latest snapshot and previous prices for each monitored tool.
    Used by the dashboard to show current pricing status and changes.
    """
    tool_names = [r[0] for r in db.query(Snapshot.tool_name).distinct().all()]
    
    result = []
    for t in tool_names:
        snapshots = (
            db.query(Snapshot)
            .filter(Snapshot.tool_name == t)
            .order_by(Snapshot.created_at.desc())
            .limit(2)
            .all()
        )
        if snapshots:
            latest = snapshots[0]
            data = _snapshot_to_dict(latest)
            if len(snapshots) > 1:
                prev = snapshots[1]
                prev_data = _snapshot_to_dict(prev)
                data["previous_prices_found"] = prev_data.get("prices_found", [])
                data["previous_tiers"] = prev_data.get("tiers", [])
            else:
                data["previous_prices_found"] = []
                data["previous_tiers"] = []
            result.append(data)

    return result


@app.get("/changes")
def get_changes(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """
    Return recent detected changes, newest first.
    """
    changes = (
        db.query(Change)
        .order_by(Change.detected_at.desc())
        .limit(limit)
        .all()
    )
    return [_change_to_dict(c) for c in changes]


@app.get("/latest")
def get_latest(db: Session = Depends(get_db)):
    """Return the 5 most recent changes (for dashboard header cards)."""
    changes = (
        db.query(Change)
        .order_by(Change.detected_at.desc())
        .limit(5)
        .all()
    )
    return [_change_to_dict(c) for c in changes]


@app.post("/run-check")
async def trigger_check():
    """
    Manually trigger an immediate scrape of all tools.
    Returns once all scrapers have completed (or timed out).
    """
    logger.info("[API] Manual /run-check triggered")
    summary = await run_all_scrapers()
    return {"status": "completed", **summary}
