"""
Gemeinsame Test-Infrastruktur.

Wichtig: Die Umgebungsvariablen werden VOR dem Import der Anwendung gesetzt,
damit engine/settings auf die SQLite-Testdatenbank zeigen.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET_KEY"] = "test-secret-not-for-production-0123456789abcdef"
os.environ["MOCK_BEDROCK"] = "true"
os.environ["SESSION_TTL_HOURS"] = "24"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Agent, ChatSession, Role, User  # noqa: E402
from app.security.password import hash_password  # noqa: E402
from app.utils import utcnow  # noqa: E402
from datetime import timedelta  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    """Frische DB-Session pro Test; Inhalte werden am Ende entfernt (Reihenfolge beachten)."""
    session = SessionLocal()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def client():
    return TestClient(app)


def make_role(db, name):
    role = db.query(Role).filter(Role.name == name).first()
    if role is None:
        role = Role(name=name)
        db.add(role)
        db.commit()
    return role


def make_user(db, email, password="password123", *, name=None, roles=(), is_admin=False):
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name or email.split("@")[0],
        is_admin=is_admin,
        roles=list(roles),
    )
    db.add(user)
    db.commit()
    return user


def make_agent(db, name, slug, *, roles=(), is_active=True, system_prompt="SEHR GEHEIMER SYSTEM-PROMPT"):
    agent = Agent(
        name=name,
        slug=slug,
        description=f"Beschreibung von {name}",
        system_prompt=system_prompt,
        model_id="test-model-id",
        is_active=is_active,
        roles=list(roles),
    )
    db.add(agent)
    db.commit()
    return agent


def login(client, email, password="password123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_session(db, user, agent, *, expired=False):
    chat_session = ChatSession(
        user_id=user.id,
        agent_id=agent.id,
        expires_at=utcnow() - timedelta(hours=1) if expired else utcnow() + timedelta(hours=24),
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session
