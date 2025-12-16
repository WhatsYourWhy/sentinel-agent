"""Repository functions for alert persistence and correlation."""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from ..database.schema import Alert


def find_recent_alert_by_key(
    session: Session,
    correlation_key: str,
    within_days: int = 7,
) -> Optional[Alert]:
    """
    Find the most recent alert with the given correlation key within the specified days.
    
    Uses ISO 8601 string comparison for reliable date filtering (SQLite stores as TEXT).
    
    Args:
        session: SQLAlchemy session
        correlation_key: Correlation key to search for
        within_days: How many days back to look (default 7)
        
    Returns:
        Most recent Alert with matching key, or None if not found
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    cutoff_iso = cutoff.isoformat()  # ISO 8601 string for lexicographic comparison

    q = session.query(Alert).filter(Alert.correlation_key == correlation_key)

    # Get all alerts with matching key, ordered by last_seen_utc
    alerts = q.order_by(Alert.last_seen_utc.desc().nullslast()).all()
    
    # Filter by date using ISO string comparison (works because ISO 8601 is lexicographically sortable)
    for alert in alerts:
        if alert.last_seen_utc:
            # Convert to ISO string if it's a datetime object (shouldn't happen, but be safe)
            if isinstance(alert.last_seen_utc, datetime):
                alert_iso = alert.last_seen_utc.isoformat()
            else:
                alert_iso = str(alert.last_seen_utc)
            
            # Lexicographic comparison works for ISO 8601 strings
            if alert_iso >= cutoff_iso:
                return alert
    
    # If no alerts with valid dates within window, return None (don't return old alerts)
    return None


def load_root_event_ids(alert_row: Alert) -> list[str]:
    """Load root_event_ids from JSON string."""
    if not alert_row.root_event_ids_json:
        return []
    try:
        return json.loads(alert_row.root_event_ids_json)
    except (json.JSONDecodeError, TypeError):
        return []


def save_root_event_ids(alert_row: Alert, ids: list[str]) -> None:
    """Save root_event_ids as JSON string (sorted, deduplicated)."""
    alert_row.root_event_ids_json = json.dumps(sorted(set(ids)))


def upsert_new_alert_row(
    session: Session,
    *,
    alert_id: str,
    summary: str,
    risk_type: str,
    classification: int,
    status: str,
    reasoning: str | None,
    recommended_actions: str | None,
    root_event_id: str,
    correlation_key: str,
) -> Alert:
    """
    Create a new alert row in the database.
    
    Args:
        session: SQLAlchemy session
        alert_id: Unique alert ID
        summary: Alert summary
        risk_type: Risk type
        classification: Classification (0-2)
        status: Status string
        reasoning: Reasoning text (can be None)
        recommended_actions: Recommended actions text (can be None)
        root_event_id: Root event ID
        correlation_key: Correlation key
        
    Returns:
        Created Alert row
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()  # Store as ISO 8601 string for consistency

    row = Alert(
        alert_id=alert_id,
        summary=summary,
        risk_type=risk_type,
        classification=classification,
        status=status,
        root_event_id=root_event_id,
        reasoning=reasoning,
        recommended_actions=recommended_actions,
        correlation_key=correlation_key,
        first_seen_utc=now_iso,  # ISO string for consistent storage
        last_seen_utc=now_iso,   # ISO string for consistent storage
        update_count=0,
    )
    save_root_event_ids(row, [root_event_id])
    session.add(row)
    return row


def update_existing_alert_row(
    session: Session,
    row: Alert,
    *,
    new_summary: str,
    new_classification: int,
    root_event_id: str,
) -> Alert:
    """
    Update an existing alert row with new information.
    
    Args:
        session: SQLAlchemy session
        row: Existing Alert row to update
        new_summary: New summary text
        new_classification: New classification (takes max of old and new)
        root_event_id: New root event ID to add to list
        
    Returns:
        Updated Alert row
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()  # Store as ISO 8601 string for consistency

    row.summary = new_summary
    row.classification = max(row.classification or 0, new_classification)
    row.status = "UPDATED"
    row.last_seen_utc = now_iso  # ISO string for consistent storage
    row.update_count = (row.update_count or 0) + 1

    ids = load_root_event_ids(row)
    if root_event_id not in ids:
        ids.append(root_event_id)
    save_root_event_ids(row, ids)

    session.add(row)
    return row

