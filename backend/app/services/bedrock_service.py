"""
Amazon Bedrock Integration - isoliert vom restlichen Backend.

Die einzige Stelle im Code, die mit AWS spricht. Alle Fachlogik ruft nur
BedrockService.generate_response(...) auf - dadurch kann das Modell oder
der Provider später zentral ausgetauscht werden.

Verwendet die Bedrock Runtime Converse API (einheitliche Schnittstelle für
alle unterstützten Modelle). AWS-Credentials kommen aus der Standard-Credential-
Chain (IAM Role, Container-Rolle, lokale AWS-CLI-Konfiguration) - NIE hart
codiert.

Streaming-Vorbereitung: generate_response liefert die vollständige Antwort.
Für Streaming später hier einfach ConverseStream aufrufen und die Chunks als
SSE an den Client reichen - die Endpoint-Struktur ändert sich dadurch nicht.
"""

import logging
from dataclasses import dataclass

import boto3

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class BedrockResult:
    text: str
    input_tokens: int
    output_tokens: int


class BedrockError(Exception):
    """Fehler bei der Kommunikation mit Amazon Bedrock."""


class MockBedrockService:
    """Lokaler Mock ohne AWS - für Entwicklung und Tests (MOCK_BEDROCK=true)."""

    def generate_response(self, *, system_prompt: str, messages: list[dict], model_id: str) -> BedrockResult:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        text = (
            "[MOCK-MODUS] Keine echte Bedrock-Anfrage gesendet (MOCK_BEDROCK=true).\n\n"
            f"Simulierte Antwort auf: {last_user[:200]}"
        )
        return BedrockResult(text=text, input_tokens=len(last_user.split()) + len(system_prompt.split()), output_tokens=32)


class BedrockService:
    """Kapselt die Amazon Bedrock Runtime Converse API."""

    def __init__(self, region: str | None = None):
        settings = get_settings()
        self.region = region or settings.AWS_REGION
        self._client = None

    def _get_client(self):
        # Standard-AWS-Credential-Chain: IAM Role / Umgebungsprofil / AWS-CLI
        if self._client is None:
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def generate_response(self, *, system_prompt: str, messages: list[dict], model_id: str) -> BedrockResult:
        """Führt einen Converse-Aufruf aus.

        Args:
            system_prompt: System-Prompt des Agents (aus der Datenbank, serverseitig geladen)
            messages: Chat-Historie im Converse-Format [{"role": "user"|"assistant", "content": "..."}]
            model_id: Bedrock Model-Identifier oder Application-Inference-Profile-ARN
                     (kommt zentral aus der Agent-Konfiguration)
        """
        if not messages:
            raise BedrockError("Keine Nachrichten übergeben")

        try:
            response = self._get_client().converse(
                modelId=model_id,
                system=[{"text": system_prompt}] if system_prompt else None,
                messages=[
                    {
                        "role": m["role"],
                        "content": [{"text": m["content"]}],
                    }
                    for m in messages
                ],
            )
        except Exception as exc:  # boto3 ClientError / ValidationError etc.
            logger.warning("Bedrock-Aufruf fehlgeschlagen (model_id=%s, error=%s)", model_id, type(exc).__name__)
            raise BedrockError("Antwortgenerierung fehlgeschlagen") from exc

        try:
            text = response["output"]["message"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BedrockError("Unerwartetes Bedrock-Antwortformat") from exc

        usage = response.get("usage", {})
        return BedrockResult(
            text=text,
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
        )


def get_bedrock_service() -> BedrockService | MockBedrockService:
    """Factory: echten oder Mock-Service je nach Konfiguration."""
    settings = get_settings()
    if settings.MOCK_BEDROCK:
        return MockBedrockService()
    return BedrockService()
