"""
Idempotentes Seed-Script: Rollen, Admin-Benutzer, Demo-Benutzer und Beispiel-Agents.

Ausführen:  python scripts/seed.py
Wird beim Container-Start automatisch ausgeführt, wenn SEED_ON_START=true.
"""

import sys

sys.path.insert(0, ".")

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Agent, Role, User
from app.security.password import hash_password

settings = get_settings()

ROLE_NAMES = ["IT", "Logistik", "Kundenservice", "Einkauf", "Buchhaltung", "Disposition"]

AGENTS = [
    {
        "name": "IT Support",
        "slug": "it-support",
        "description": "Unterstützung bei IT-Störungen, Zugriffen, Hardware und Software.",
        "roles": ["IT"],
        "system_prompt": (
            "Du bist der interne IT-Support-Assistent der Firma.\n\n"
            "Deine Aufgabe ist es, Mitarbeiter bei IT-Fragestellungen zu unterstützen.\n\n"
            "Regeln:\n"
            "- Antworte auf Deutsch.\n"
            "- Sei präzise und sachlich.\n"
            "- Erfinde keine Daten.\n"
            "- Wenn Informationen fehlen, sage ausdrücklich, dass Informationen fehlen.\n"
            "- Verwende keine Emojis.\n"
            "- Strukturiere Antworten mit Überschriften und Aufzählungen.\n"
            "- Gib keine schädlichen Sicherheits-Anweisungen (z.B. zum Umgehen von Sicherheitsmaßnahmen)."
        ),
    },
    {
        "name": "Softwareentwicklung",
        "slug": "softwareentwicklung",
        "description": "Fragen zu Architektur, Code-Reviews und internen Entwicklungsstandards.",
        "roles": ["IT"],
        "system_prompt": (
            "Du bist der interne Softwareentwicklungs-Assistent der Firma.\n\n"
            "Deine Aufgabe ist es, Entwickler bei Architektur-, Code- und Review-Fragen zu unterstützen.\n\n"
            "Regeln:\n"
            "- Antworte auf Deutsch.\n"
            "- Sei präzise und sachlich.\n"
            "- Erfinde keine Daten.\n"
            "- Wenn Informationen fehlen, sage ausdrücklich, dass Informationen fehlen.\n"
            "- Verwende keine Emojis.\n"
            "- Strukturiere Antworten mit Überschriften und Aufzählungen."
        ),
    },
    {
        "name": "Logistik",
        "slug": "logistik",
        "description": "Hilfe bei logistischen Fragestellungen, Auftragsstatus und Disposition.",
        "roles": ["Logistik", "Disposition"],
        "system_prompt": (
            "Du bist der interne Logistik-Assistent der Firma.\n\n"
            "Deine Aufgabe ist es, Mitarbeiter bei logistischen Fragestellungen zu unterstützen.\n\n"
            "Regeln:\n"
            "- Antworte auf Deutsch.\n"
            "- Sei präzise und sachlich.\n"
            "- Erfinde keine Daten.\n"
            "- Wenn Informationen fehlen, sage ausdrücklich, dass Informationen fehlen.\n"
            "- Verwende keine Emojis.\n"
            "- Strukturiere Antworten mit Überschriften und Aufzählungen."
        ),
    },
    {
        "name": "Kundenservice",
        "slug": "kundenservice",
        "description": "Antwortvorlagen und Prozessunterstützung für Kundenanfragen.",
        "roles": ["Kundenservice"],
        "system_prompt": (
            "Du bist der interne Kundenservice-Assistent der Firma.\n\n"
            "Deine Aufgabe ist es, Service-Mitarbeiter bei der Beantwortung von Kundenanfragen zu unterstützen.\n\n"
            "Regeln:\n"
            "- Antworte auf Deutsch.\n"
            "- Sei freundlich, präzise und sachlich.\n"
            "- Erfinde keine Daten.\n"
            "- Wenn Informationen fehlen, sage ausdrücklich, dass Informationen fehlen.\n"
            "- Verwende keine Emojis.\n"
            "- Strukturiere Antworten mit Überschriften und Aufzählungen."
        ),
    },
    {
        "name": "Einkauf",
        "slug": "einkauf",
        "description": "Unterstützung bei Bestellungen, Lieferanten und Beschaffungsprozessen.",
        "roles": ["Einkauf"],
        "system_prompt": (
            "Du bist der interne Einkaufs-Assistent der Firma.\n\n"
            "Deine Aufgabe ist es, Mitarbeiter bei Beschaffungs- und Lieferantenfragen zu unterstützen.\n\n"
            "Regeln:\n"
            "- Antworte auf Deutsch.\n"
            "- Sei präzise und sachlich.\n"
            "- Erfinde keine Daten.\n"
            "- Wenn Informationen fehlen, sage ausdrücklich, dass Informationen fehlen.\n"
            "- Verwende keine Emojis.\n"
            "- Strukturiere Antworten mit Überschriften und Aufzählungen."
        ),
    },
]


def seed(db: Session) -> None:
    roles = {}
    for name in ROLE_NAMES:
        role = db.query(Role).filter(Role.name == name).first()
        if role is None:
            role = Role(name=name)
            db.add(role)
        roles[name] = role
    db.flush()

    # Admin (Plattform-Administrator)
    if not db.query(User).filter(User.email == settings.SEED_ADMIN_EMAIL.lower()).first():
        db.add(
            User(
                email=settings.SEED_ADMIN_EMAIL.lower(),
                password_hash=hash_password(settings.SEED_ADMIN_PASSWORD),
                name="Administrator",
                is_admin=True,
                roles=[roles["IT"]],
            )
        )
        print(f"Admin-Benutzer angelegt: {settings.SEED_ADMIN_EMAIL}")

    # Demo-Benutzer mit Rolle IT
    if not db.query(User).filter(User.email == settings.SEED_DEMO_USER_EMAIL.lower()).first():
        db.add(
            User(
                email=settings.SEED_DEMO_USER_EMAIL.lower(),
                password_hash=hash_password(settings.SEED_DEMO_USER_PASSWORD),
                name="Fabio",
                is_admin=False,
                roles=[roles["IT"]],
            )
        )
        print(f"Demo-Benutzer angelegt: {settings.SEED_DEMO_USER_EMAIL}")

    # Beispiel-Agents
    for spec in AGENTS:
        if not db.query(Agent).filter(Agent.slug == spec["slug"]).first():
            db.add(
                Agent(
                    name=spec["name"],
                    slug=spec["slug"],
                    description=spec["description"],
                    system_prompt=spec["system_prompt"],
                    model_id=settings.BEDROCK_DEFAULT_MODEL_ID,
                    roles=[roles[r] for r in spec["roles"]],
                )
            )
            print(f"Agent angelegt: {spec['name']}")

    db.commit()
    print("Seed abgeschlossen.")


if __name__ == "__main__":
    seed(SessionLocal())
