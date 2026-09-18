"""
KnowledgeService - vorbereitete Schnittstelle für RAG (noch NICHT implementiert).

Der MVP arbeitet ausschließlich mit System-Prompt + Session-Kontext.
Diese Klasse ist der spätere Andockpunkt für eine Knowledge-/RAG-Schicht:

    User Question
        -> KnowledgeService.retrieve(agent, query)   # hier: [] (leer)
        -> relevante Dokumente als Kontext anreichern
        -> Bedrock Converse API

Spätere Implementierungen (OpenSearch, Bedrock Knowledge Bases, Aurora PgVector,
...) implementieren nur retrieve() - der Chat-Endpoint bleibt unverändert.
"""


class KnowledgeService:
    def retrieve(self, agent, query: str) -> list[str]:
        """Gibt relevante Wissens-Fragmente für eine Anfrage zurück.

        MVP: immer leer (kein RAG im Scope dieses Milestones).
        """
        return []
