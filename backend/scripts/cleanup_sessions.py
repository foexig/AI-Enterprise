"""
Aufräum-Job: löscht abgelaufene Sessions inklusive Nachrichten gemäß
CHAT_RETENTION_DAYS (Datenschutz: konfigurierbare Aufbewahrungsdauer).

Später als Cron-Job / ECS Scheduled Task / Lambda ausführen, z.B. täglich:

    python scripts/cleanup_sessions.py

Der MVP selbst ruft das Skript NICHT automatisch auf.
"""

import sys
from datetime import timedelta

sys.path.insert(0, ".")

from app.config import get_settings
from app.database import SessionLocal
from app.models import ChatSession
from app.utils import utcnow


def cleanup() -> int:
    settings = get_settings()
    cutoff = utcnow() - timedelta(days=settings.CHAT_RETENTION_DAYS)
    with SessionLocal() as db:
        # Sessions, deren Aufbewahrungsfrist abgelaufen ist
        expired = db.query(ChatSession).filter(ChatSession.last_activity_at < cutoff).all()
        count = len(expired)
        for session in expired:
            db.delete(session)  # Nachrichten werden per CASCADE mitgelöscht
        db.commit()
    print(f"{count} Session(s) gelöscht (Aufbewahrung: {settings.CHAT_RETENTION_DAYS} Tage).")
    return count


if __name__ == "__main__":
    cleanup()
