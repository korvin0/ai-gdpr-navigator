"""Simple CSV analytics for phase funnel events."""

import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiogram.types import User

logger = logging.getLogger(__name__)

FIELDNAMES = [
    "timestamp_utc",
    "telegram_user_id",
    "username",
    "full_name",
    "phase",
    "event",
    "fsm_state",
    "gdpr_mandatory",
    "gdpr_status",
    "ai_act_status",
    "ai_type",
]


def _analytics_csv_path() -> Path:
    """Resolve analytics path after .env has been loaded."""
    return Path(os.getenv("ANALYTICS_CSV_PATH", "analytics_events.csv"))


def _stringify(value: Any) -> str:
    """Convert values to stable CSV strings."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def log_event(user: User | None, phase: str, event: str, state: dict | None = None) -> None:
    """Append a single analytics event to the CSV log."""
    state = state or {}
    row = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "telegram_user_id": _stringify(user.id if user else None),
        "username": _stringify(user.username if user else None),
        "full_name": _stringify(user.full_name if user else None),
        "phase": phase,
        "event": event,
        "fsm_state": _stringify(state.get("state")),
        "gdpr_mandatory": _stringify(state.get("gdpr_mandatory")),
        "gdpr_status": _stringify(state.get("gdpr_status")),
        "ai_act_status": _stringify(state.get("ai_act_status")),
        "ai_type": _stringify(state.get("ai_type") or state.get("target")),
    }

    try:
        analytics_csv_path = _analytics_csv_path()
        analytics_csv_path.parent.mkdir(parents=True, exist_ok=True)
        should_write_header = (
            not analytics_csv_path.exists() or analytics_csv_path.stat().st_size == 0
        )
        with analytics_csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
            if should_write_header:
                writer.writeheader()
            writer.writerow(row)
    except OSError:
        logger.exception("Failed to write analytics event")
