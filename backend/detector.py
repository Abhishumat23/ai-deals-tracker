"""
Change detection logic.
Compares new scrape results against the last stored snapshot.
Writes a Change record when differences are found.
"""

import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from models import Snapshot, Change
from utils import hash_content, normalize_text, build_diff_summary, extract_price_mentions, truncate

logger = logging.getLogger(__name__)


def process_scrape_result(db: Session, tool_name: str, scrape_data: dict) -> Change | None:
    """
    Given a fresh scrape result, check whether it differs from the last snapshot.

    Args:
        db: Active SQLAlchemy session
        tool_name: e.g. "OpenAI"
        scrape_data: dict returned by the scraper (must contain "raw_text")

    Returns:
        A Change ORM object if a change was detected, otherwise None.
    """
    raw_text = scrape_data.get("raw_text", "")
    if not raw_text:
        logger.warning(f"[{tool_name}] Empty raw_text, skipping")
        return None

    new_hash = hash_content(raw_text)
    normalized_new = normalize_text(raw_text)

    # Get the most recent snapshot for this tool
    last_snapshot: Snapshot | None = (
        db.query(Snapshot)
        .filter(Snapshot.tool_name == tool_name)
        .order_by(Snapshot.created_at.desc())
        .first()
    )

    # Always save a new snapshot regardless of change
    new_snapshot = Snapshot(
        tool_name=tool_name,
        content_hash=new_hash,
        raw_content=truncate(normalized_new, 10_000),  # cap storage size
        structured_json=json.dumps(scrape_data),
        created_at=datetime.utcnow(),
    )
    db.add(new_snapshot)

    if last_snapshot is None:
        # First time we've seen this tool — save snapshot but no change record
        logger.info(f"[{tool_name}] First snapshot saved (hash={new_hash[:8]})")
        return None

    if last_snapshot.content_hash == new_hash:
        logger.info(f"[{tool_name}] No change detected (hash={new_hash[:8]})")
        return None

    # Hashes differ — content changed
    logger.info(f"[{tool_name}] ⚡ Change detected! old={last_snapshot.content_hash[:8]} new={new_hash[:8]}")

    old_text = last_snapshot.raw_content or ""
    diff = build_diff_summary(old_text, normalized_new)

    # Build a concise human-readable summary
    old_prices = extract_price_mentions(old_text)
    new_prices = extract_price_mentions(normalized_new)
    price_note = ""
    if old_prices != new_prices:
        price_note = f"\nPrices before: {', '.join(old_prices) or 'none found'}\nPrices after:  {', '.join(new_prices) or 'none found'}"

    summary = f"Content changed on {tool_name} pricing page.{price_note}\n\nDiff (first 30 lines):\n{diff}"

    change = Change(
        tool_name=tool_name,
        old_content=truncate(old_text, 3_000),
        new_content=truncate(normalized_new, 3_000),
        summary=truncate(summary, 4_000),
        detected_at=datetime.utcnow(),
    )
    db.add(change)

    return change
