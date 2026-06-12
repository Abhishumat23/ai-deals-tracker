"""
Change detection logic.
Compares new scrape results against the last stored snapshot.
Writes a Change record when differences are found.
"""

import json
import logging
import re
from datetime import datetime
from sqlalchemy.orm import Session

from models import Snapshot, Change
from utils import hash_content, normalize_text, build_diff_summary, extract_price_mentions, truncate

logger = logging.getLogger(__name__)


def format_price_display(price: str, billing_cycle: str) -> str:
    if not price or price.lower() in ("free", "not found", "see website"):
        return price
        
    # Strip any existing billing or unit suffixes (user, seat, mo, yr, etc.) globally
    cleaned_price = re.sub(r'/(?:user|seat|mo|month|yr|year)\b', '', price, flags=re.IGNORECASE).strip()
    
    if cleaned_price.endswith('/'):
        cleaned_price = cleaned_price[:-1].strip()
        
    if billing_cycle == "monthly":
        if "user" in price.lower():
            return f"{cleaned_price}/user/mo"
        elif "seat" in price.lower():
            return f"{cleaned_price}/seat/mo"
        return f"{cleaned_price}/mo"
    elif billing_cycle == "annually":
        if "user" in price.lower():
            return f"{cleaned_price}/user/yr"
        elif "seat" in price.lower():
            return f"{cleaned_price}/seat/yr"
        return f"{cleaned_price}/yr"
        
    return cleaned_price


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

    # Hashes differ — content changed (visually or pricing)
    logger.info(f"[{tool_name}] ⚡ Hash difference detected! old={last_snapshot.content_hash[:8]} new={new_hash[:8]}")

    old_text = last_snapshot.raw_content or ""
    diff = build_diff_summary(old_text, normalized_new)

    # Calculate structured pricing changes
    new_tiers = scrape_data.get("tiers", [])
    old_tiers = []
    
    if last_snapshot.structured_json:
        try:
            old_data = json.loads(last_snapshot.structured_json)
            old_tiers = old_data.get("tiers", [])
        except Exception as e:
            logger.warning(f"[{tool_name}] Failed to parse last snapshot structured_json: {e}")
            
    structured_changes = []
    
    # Helper to parse numeric values for increase/decrease check
    def parse_numeric(price_str):
        if not price_str or any(w in price_str.lower() for w in ("free", "not found", "see website")):
            return 0.0
        match = re.search(r'[\d,]+(?:\.\d+)?', price_str)
        if match:
            return float(match.group(0).replace(',', ''))
        return 0.0

    # Match each new tier to old tier by name
    for t in new_tiers:
        tier_name = t.get("name", "Unknown")
        pt = None
        for pot in old_tiers:
            if pot.get("name", "").lower() == tier_name.lower():
                pt = pot
                break
                
        # Format prices using the fallback cycle logic
        curr_cycle = t.get("billing_cycle") or "Unpublished"
        prev_cycle = pt.get("billing_cycle") if pt else "Unpublished"
        if not prev_cycle or prev_cycle == "Unpublished":
            prev_cycle = curr_cycle
            
        new_price = format_price_display(t.get("price") or "", curr_cycle)
        
        if pt:
            old_price = format_price_display(pt.get("price") or "", prev_cycle)
            if old_price != new_price:
                # Price changed!
                old_val = parse_numeric(old_price)
                new_val = parse_numeric(new_price)
                
                if old_price.lower() == "not found" or new_price.lower() == "not found":
                    change_type = "price_change"
                elif new_val > old_val:
                    change_type = "price_increase"
                elif new_val < old_val:
                    change_type = "price_decrease"
                else:
                    change_type = "pricing_structure_change"
                    
                structured_changes.append({
                    "type": change_type,
                    "plan": tier_name,
                    "old_price": old_price,
                    "new_price": new_price
                })
        else:
            # New plan added
            if new_price.lower() != "not found":
                structured_changes.append({
                    "type": "new_plan",
                    "plan": tier_name,
                    "old_price": None,
                    "new_price": new_price
                })
                
    # Check for removed plans
    for pt in old_tiers:
        tier_name = pt.get("name", "Unknown")
        matched = False
        for nt in new_tiers:
            if nt.get("name", "").lower() == tier_name.lower():
                matched = True
                break
        if not matched:
            old_price = format_price_display(pt.get("price") or "", pt.get("billing_cycle") or "Unpublished")
            if old_price.lower() != "not found":
                structured_changes.append({
                    "type": "plan_removed",
                    "plan": tier_name,
                    "old_price": old_price,
                    "new_price": None
                })

    # If no price values actually changed, ignore visual-only changes
    if not structured_changes:
        logger.info(f"[{tool_name}] Visual/structural change detected, but no price values changed — skipping change record")
        return None

    # Build a concise human-readable summary
    notes = []
    for chg in structured_changes:
        ptype = chg["type"]
        plan = chg["plan"]
        old_p = chg["old_price"]
        new_p = chg["new_price"]
        if ptype == "price_increase":
            notes.append(f"[Price Increased] {plan}: {old_p} -> {new_p}")
        elif ptype == "price_decrease":
            notes.append(f"[Price Decreased] {plan}: {old_p} -> {new_p}")
        elif ptype == "new_plan":
            notes.append(f"[New Plan Added] {plan}: {new_p}")
        elif ptype == "plan_removed":
            notes.append(f"[Plan Removed] {plan} (was: {old_p})")
        else:
            notes.append(f"[Plan Updated] {plan}: {old_p} -> {new_p}")
            
    price_note = "\n" + "\n".join(notes)
    summary = f"Content changed on {tool_name} pricing page.{price_note}\n\nDiff (first 30 lines):\n{diff}"

    change = Change(
        tool_name=tool_name,
        old_content=truncate(old_text, 3_000),
        new_content=truncate(normalized_new, 3_000),
        summary=truncate(summary, 4_000),
        structured_change_json=json.dumps(structured_changes),
        detected_at=datetime.utcnow(),
    )
    db.add(change)

    return change
