from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naives UTC-Datetime (portabel für PostgreSQL und SQLite, konsistent im ganzen Projekt)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
