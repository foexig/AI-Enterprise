from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentOut(BaseModel):
    """Agent-Ausgabe für normale Benutzer: KEIN System-Prompt, KEINE Rolle-Details.

    Der System-Prompt und die interne Konfiguration sind vertraulich und werden
    ausschließlich über die Admin-API (schemas/admin.py) ausgeliefert.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str
