"""
Stellt Beschreibung und System-Prompt der Seed-Agents auf den Ursprungszustand wieder her.

Hintergrund: Ein UI-Bug im Admin-Bereich konnte beim Wechseln des Agents die
angezeigten (veralteten) Feldwerte in den neu gewählten Agent zurückschreiben.
Dieses Script setzt die Agent-Definitionen wieder auf den Seed-Zustand.

Betrifft NUR Agents, deren slug einem Seed-Agent entspricht
(it-support, softwareentwicklung, logistik, kundenservice, einkauf, buchhaltung).
Eigene Agents bleiben vollständig unberührt; Rollen-Zuordnungen und
Aktiv-Status bleiben unverändert.

Ausführen:  python scripts/restore_seed_agents.py
"""

import sys

sys.path.insert(0, ".")

from app.database import SessionLocal
from app.models import Agent
from scripts.seed import AGENTS


def main() -> None:
    db = SessionLocal()
    updated = 0
    try:
        for seed in AGENTS:
            agent = db.query(Agent).filter_by(slug=seed["slug"]).first()
            if agent is None:
                continue
            agent.name = seed["name"]
            agent.description = seed["description"]
            agent.system_prompt = seed["system_prompt"]
            updated += 1
        db.commit()
        print(f"{updated} Seed-Agent(s) auf Ursprungszustand wiederhergestellt.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
