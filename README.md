# Enterprise AI Platform (MVP)

Interne Enterprise-AI-Webplattform: mehrere voneinander getrennte AI-Agents (IT, Kundenservice, Logistik, Einkauf, Buchhaltung, ...), die von Amazon Bedrock angetrieben werden. Benutzer sehen ausschließlich die Agents, für die sie über ihre Rollen freigeschaltet sind.

```
Browser → Next.js → FastAPI → Auth/Berechtigungsprüfung → Agent-Konfiguration → Bedrock Converse API → Antwort → Browser
```

Der Client ruft Bedrock **niemals direkt** auf. AWS-Credentials verlassen das Backend nicht.

---

## 1. Architektur

| Komponente | Technologie |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, eigenes CSS (keine UI-Library) |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2 |
| Datenbank | PostgreSQL 16 |
| AI | Amazon Bedrock Runtime, Converse API (boto3), zentrale `BedrockService`-Klasse |
| Auth | Einfache Benutzerverwaltung, bcrypt-Hashes, JWT (kapselbar für Cognito/Entra ID) |
| Betrieb | Docker / Docker Compose (lokal), AWS-fähig (ECS/Fargate, RDS) |

### Projektstruktur

```
/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI-App, CORS, Router-Registrierung
│   │   ├── config.py            Zentrale Einstellungen (pydantic-settings, .env)
│   │   ├── database.py          Engine / Session / get_db
│   │   ├── utils.py             utcnow() Helfer
│   │   ├── models/              SQLAlchemy-Modelle
│   │   │   ├── user.py          User, Role, user_roles
│   │   │   ├── agent.py         Agent, agent_roles
│   │   │   ├── chat.py          ChatSession, ChatMessage
│   │   │   └── usage.py         UsageRecord (Kostenüberwachung)
│   │   ├── schemas/             Pydantic-Schemas (API-Verträge)
│   │   ├── api/                 Endpunkte
│   │   │   ├── auth.py          Login / Logout / Me
│   │   │   ├── agents.py        Agent-Liste, Agent-Detail, Sessions
│   │   │   ├── chat.py          Nachrichten senden/lesen
│   │   │   └── admin.py         Admin-CRUD (users, roles, agents)
│   │   ├── services/
│   │   │   ├── bedrock_service.py   Bedrock Converse API (einzige AWS-Stelle) + Mock
│   │   │   └── knowledge_service.py  RAG-Schnittstelle (Stub, kein RAG im MVP)
│   │   └── security/
│   │       ├── password.py      bcrypt Hashing
│   │       ├── tokens.py        JWT erzeugen/prüfen (Austauschpunkt für SSO)
│   │       ├── deps.py          get_current_user / get_current_admin
│   │       └── authorization.py Agent-/Session-Berechtigungsprüfungen
│   ├── alembic/                 DB-Migrationen
│   ├── scripts/
│   │   ├── seed.py              Rollen, Admin, Demo-User, Beispiel-Agents (idempotent)
│   │   └── cleanup_sessions.py  Aufbewahrungsdauer-Job (CHAT_RETENTION_DAYS)
│   └── tests/                   pytest-Tests der kritischen Autorisierungsfälle
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx         Chat (Sidebar mit freigegebenen Agents)
│       │   ├── login/page.tsx   Anmeldung
│       │   └── admin/page.tsx   Admin-Bereich (Agents, Benutzer, Rollen)
│       └── lib/                 API-Client + Typen
├── docker/                      Dockerfiles + Backend-Entrypoint
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 2. Schnellstart (lokal mit Docker Compose)

Voraussetzungen: Docker + Docker Compose.

```bash
cp .env.example .env
# .env bearbeiten: JWT_SECRET_KEY und Passwörter setzen!
#   JWT-Secret erzeugen:  python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (`/health`, OpenAPI-Dokumentation via `DEBUG=true` unter `/docs`)
- PostgreSQL: localhost:5432

**Standard-Seed-Zugänge** (in `.env` ändern!):

| Benutzer | E-Mail | Passwort (aus .env) | Rollen |
|---|---|---|---|
| Admin | `admin@example.com` | `SEED_ADMIN_PASSWORD` | IT, Plattform-Admin |
| Demo | `fabio@example.com` | `SEED_DEMO_USER_PASSWORD` | IT |

Der Container führt beim Start automatisch `alembic upgrade head` aus und seedet bei `SEED_ON_START=true` idempotent.

**Ohne AWS starten:** `MOCK_BEDROCK=true` (Standard in `.env.example`) liefert simulierte Antworten, damit die Plattform lokal ohne AWS-Credentials lauffähig ist. Für echte Antworten: `MOCK_BEDROCK=false` setzen (siehe Abschnitt 4).

---

## 3. Datenbank-Migrationen (Alembic)

Migrationen werden beim Container-Start automatisch ausgeführt. Manuell:

```bash
cd backend

# Neue Migration nach Modelländerung erzeugen
alembic revision --autogenerate -m "kurze beschreibung"

# Migrationen anwenden
alembic upgrade head

# Aktuellen Stand prüfen
alembic current
```

Die `DATABASE_URL` kommt zentral aus `.env` bzw. den Umgebungsvariablen (siehe `alembic/env.py`).

---

## 4. AWS-Bedrock-Konfiguration

### 4.1 Modellzugriff aktivieren

1. AWS-Konsole → Amazon Bedrock → **Model access** → gewünschte Modelle aktivieren (z.B. `Anthropic Claude 3.5 Sonnet`, Region `eu-central-1`).
2. Alternativ/professionell: **Application Inference Profiles** anlegen (Konsole oder `aws bedrock create-inference-profile`) und die Profil-ARN als `model_id` im Agent hinterlegen - das ermöglicht saubere Kostenzuordnung pro Agent/Team.

### 4.2 Backend konfigurieren

```env
MOCK_BEDROCK=false
AWS_REGION=eu-central-1
```

Modelle werden **pro Agent** im Admin-Bereich gesetzt (`model_id`), z.B.:

- Foundation-Model-ID: `eu.anthropic.claude-3-5-sonnet-20241022-v2:0`
- Inference-Profile-ARN: `arn:aws:bedrock:eu-central-1:123456789012:inference-profile/MeinTeamProfil`

Die Model-ID steht nur an einer Stelle (Agent-Konfiguration in der DB) - nirgends hart codiert.

### 4.3 IAM-Berechtigungen

Für die Ausführungsrolle (ECS Task Role / EC2 Instance Profile) genügt:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": [
        "arn:aws:bedrock:*:::foundation-model/*",
        "arn:aws:bedrock:*:123456789012:inference-profile/*"
      ]
    }
  ]
}
```

AWS CLI (Richtlinie erstellen und an Rolle hängen):

```bash
aws iam create-policy --policy-name BedrockInvokePolicy --policy-document file://policy.json
aws iam attach-role-policy --role-name MeineBackendRolle --policy-arn arn:aws:iam::123456789012:policy/BedrockInvokePolicy
```

### 4.4 Credential-Chain

Das Backend nutzt **keine hart codierten Access Keys**. boto3 verwendet die Standard-Credential-Chain:

- In AWS: IAM Role (ECS Task Role / EC2 Instance Profile) - empfohlen
- Lokal: `~/.aws/credentials` (AWS-CLI-Profil), `AWS_PROFILE`-Umgebungsvariable

---

## 5. API-Endpunkte

Alle Endpunkte sind unter `/api` erreichbar. Authentifizierung: `Authorization: Bearer <JWT>`.

### Auth
| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/api/auth/login` | Anmeldung → JWT + Benutzerdaten |
| POST | `/api/auth/logout` | Logout (Client verwirft Token) |
| GET | `/api/auth/me` | Aktueller Benutzer + Rollen |

### Agents & Chat (Benutzer)
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/api/agents` | Nur für den Benutzer freigegebene, aktive Agents |
| GET | `/api/agents/{id}` | Agent-Detail (mit serverseitiger 403-Prüfung) |
| POST | `/api/agents/{id}/sessions` | Neue Chat-Session (TTL) |
| GET | `/api/agents/{id}/sessions` | Eigene Sessions für einen Agent |
| GET | `/api/sessions/{id}/messages` | Nachrichten der eigenen Session |
| POST | `/api/sessions/{id}/messages` | Nachricht senden → AI-Antwort + Token-Nutzung |

### Admin (nur `is_admin`)
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET/POST | `/api/admin/users` | Benutzer listen/anlegen |
| PATCH | `/api/admin/users/{id}` | Benutzer ändern (Name, aktiv, Rollen, Admin) |
| GET/POST | `/api/admin/roles` | Rollen listen/anlegen |
| GET/POST | `/api/admin/agents` | Agents listen/anlegen (inkl. System-Prompt, model_id, Rollen) |
| PATCH | `/api/admin/agents/{id}` | Agent ändern (inkl. System-Prompt, Modell, aktiv) |
| POST | `/api/admin/agents/{id}/roles` | Rollen-Zuordnung des Agents ersetzen |

### Health
`GET /health` - Container-/Loadbalancer-Check.

---

## 6. Sicherheitsarchitektur

- **Passwörter**: ausschließlich bcrypt-Hashes (salted), Klartext nie gespeichert oder geloggt.
- **JWT**: signiert mit `JWT_SECRET_KEY`, Ablauf über `ACCESS_TOKEN_EXPIRE_MINUTES`. Token-Erzeugung/-Prüfung ist in `security/tokens.py` gekapselt - Austauschpunkt für AWS Cognito oder Microsoft Entra ID, ohne Endpoint-Änderungen.
- **Serverseitige Authorization bei jedem geschützten Endpoint** (Frontend-Ausblendung reicht nicht):
  - nicht authentifiziert → `401`
  - Agent existiert nicht → `404` (verhindert Enumeration)
  - Agent deaktiviert oder Rolle fehlt → `403` - auch beim **Senden einer Nachricht** wird erneut geprüft (Rolle kann während einer laufenden Session entzogen werden)
  - fremde Session-ID → `404` (Existenz wird nicht aufgedeckt)
  - abgelaufene Session (TTL) → `403`
- **Kein Prompt-Leak**: `/api/agents*` liefert für normale Benutzer bewusst KEIN `system_prompt` und kein `model_id`; vollständige Konfiguration nur über die Admin-API.
- **Kein AWS-Secret-Leak**: das Frontend erhält nur generierte Antworten; AWS-Credentials verbleiben im Backend (Standard-Credential-Chain, keine hart codierten Keys).
- **SQL-Injection-Prävention**: SQLAlchemy Core/ORM mit parametrisierten Queries.
- **CORS**: nur die konfigurierten Origins (`CORS_ORIGINS`), keine Wildcards.
- **Input-Validierung**: Pydantic-Schemas an jedem Endpoint (z.B. `content` 1-8000 Zeichen, Slug-Muster).
- **Rate Limiting**: als vorbereitete Erweiterung - Middleware-Ansatz im FastAPI-Stack möglich, ohne Fachlogik zu ändern (z.B. `slowapi` oder API-Gateway-Drosselung in AWS).
- **Logging ohne sensible Inhalte**: es werden IDs, Status und Token-Zahlen geloggt, niemals Chat-Inhalte.
- **Secrets**: `.env` ist git-ignored; `.env.example` dokumentiert alle Variablen ohne echte Werte.

### Session-Isolation

- Jede Session ist eindeutig über `user_id + agent_id + session_id`.
- **Kein globaler Firmen-Kontext**: der Bedrock-Aufruf erhält ausschließlich den System-Prompt des Agents und die Nachrichten der aktuellen Session (`MAX_HISTORY_MESSAGES` begrenzt den Kontext).
- TTL: `SESSION_TTL_HOURS` (Standard 24 h, Sliding: bei Aktivität verlängert). Nach Ablauf keine Nutzung als Kontext möglich.
- Zwei Agents desselben Benutzers haben niemals gemeinsamen Gesprächskontext.

### Datenschutz & Aufbewahrung

- Chat-Inhalte sind vertrauliche Unternehmensdaten; es wird nur gespeichert, was der MVP benötigt.
- Konfigurierbare Aufbewahrungsdauer: `CHAT_RETENTION_DAYS`; `backend/scripts/cleanup_sessions.py` löscht alte Sessions inklusive Nachrichten (CASCADE) und ist als täglicher Job (ECS Scheduled Task / Cron / Lambda) einhängbar.

### Kostenüberwachung

- Pro Bedrock-Aufruf wird ein `UsageRecord` gespeichert: `agent_id`, `user_id`, `model_id`, `input_tokens`, `output_tokens`, Zeitstempel.
- Zusammen mit **Application Inference Profiles** als `model_id` ermöglicht das später eine Kostenzuordnung pro Agent/Team in CloudWatch/Kostenberichten.

---

## 7. Tests

Die kritischen Berechtigungsfälle sind mit pytest abgedeckt (SQLite-Testdatenbank, Bedrock im Mock-Modus):

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

Getestet u.a.:

- nicht authentifiziert → 401
- User ohne Berechtigung → 403 (Liste UND direkter Aufruf `GET /api/agents/{id}`)
- User mit Berechtigung → 200
- deaktivierter Agent → kein Zugriff (403), auch mitten in einer laufenden Session
- fremde Session-ID → 404 (User kann fremde Session nicht verwenden)
- Rollenentzug während laufender Session → 403 beim Senden
- Session-Isolation zwischen zwei Agents desselben Users
- abgelaufene Session (TTL) → 403
- System-Prompt wird normalen Benutzern nie ausgeliefert
- Admin-Endpunkte ohne Admin-Rolle → 403
- Passwörter nur als bcrypt-Hash gespeichert

---

## 8. Entwicklung ohne Docker

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# PostgreSQL lokal starten und DATABASE_URL in .env setzen (Host: localhost)
alembic upgrade head && python scripts/seed.py
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## 9. Ausblick: geplante Erweiterungen

| Bereich | Vorbereitung im MVP |
|---|---|
| **RAG / Knowledge** | `KnowledgeService` als saubere Schnittstelle (`retrieve(agent, query) -> list[str]`), Aufrufpunkt im Chat-Endpoint ist vorbereitet; MVP arbeitet nur mit System-Prompt + Session-Kontext. Später: Bedrock Knowledge Bases, OpenSearch oder PgVector, ohne Endpoint-Änderung. |
| **SSO (Cognito, Microsoft Entra ID)** | JWT-Erzeugung/Prüfung in `security/tokens.py` gekapselt; User-Modell mit stabiler ID/E-Mail; Admin-Sync kann Benutzer aus externem IdP spiegeln. |
| **Streaming** | `BedrockService` kapselt den Converse-Aufruf; für Streaming wird dort `converse_stream` ergänzt und der Endpoint liefert Chunks per SSE - Fachlogik bleibt unverändert. |
| **Unternehmens-APIs / Tools** | Agents können um Service-Integrationen erweitert werden; Berechtigungsmodell (Rollen) bleibt davon unberührt. |
| **Zusätzliche Agents** | Reine Datenpflege im Admin-Bereich: Name, Slug, Prompt, Modell, Rollen - kein Code-Deploy nötig. |
| **Kosten-Controlling** | `UsageRecord`-Tabelle + Inference-Profile-ARNs pro Agent ermöglichen Auswertung pro Team/Agent. |
| **Retention/Audit** | Cleanup-Script vorhanden; Aufbewahrungsdauer konfigurierbar. |
