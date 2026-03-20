from datetime import datetime, timezone, timedelta


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def utcnow_str() -> str:
    return utcnow().isoformat()


def get_week_start(dt: datetime = None) -> str:
    """Returns ISO string for Monday 00:00 UTC of the current week."""
    if dt is None:
        dt = utcnow()
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def progress_bar(elapsed: int, total: int, length: int = 20) -> str:
    """Returns a Unicode block progress bar string."""
    filled = int(length * elapsed / total)
    bar = "█" * filled + "░" * (length - filled)
    pct = int(100 * elapsed / total)
    return f"`{bar}` {pct}%"
