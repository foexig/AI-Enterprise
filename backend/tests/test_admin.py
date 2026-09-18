"""Admin-Endpunkte müssen serverseitig geschützt sein."""

from app.models import User
from tests.conftest import login, make_agent, make_role, make_user


def test_admin_endpoints_require_admin(client, db):
    role = make_role(db, "IT")
    make_user(db, "normal@example.com", roles=[role])
    headers = login(client, "normal@example.com")
    for path, method in [
        ("/api/admin/users", "get"),
        ("/api/admin/roles", "get"),
        ("/api/admin/agents", "get"),
    ]:
        response = getattr(client, method)(path, headers=headers)
        assert response.status_code == 403, path


def test_admin_endpoints_require_auth(client, db):
    assert client.get("/api/admin/users").status_code == 401


def test_admin_full_lifecycle(client, db):
    it = make_role(db, "IT")
    make_user(db, "admin@example.com", is_admin=True, roles=[it])
    headers = login(client, "admin@example.com")

    # Rolle anlegen
    response = client.post("/api/admin/roles", headers=headers, json={"name": "Buchhaltung"})
    assert response.status_code == 201
    role_buha_id = response.json()["id"]

    # Benutzer anlegen
    response = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "email": "newuser@example.com",
            "password": "startpass123",
            "name": "Neuer User",
            "role_ids": [role_buha_id],
        },
    )
    assert response.status_code == 201
    assert response.json()["roles"] == ["Buchhaltung"]
    assert "password" not in response.json()

    # Agent anlegen mit Rolle
    response = client.post(
        "/api/admin/agents",
        headers=headers,
        json={
            "name": "Buchhaltung",
            "slug": "buchhaltung",
            "description": "Finanzfragen",
            "system_prompt": "Du bist der Buchhaltungs-Assistent.",
            "model_id": "eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
            "role_ids": [role_buha_id],
        },
    )
    assert response.status_code == 201
    agent_id = response.json()["id"]
    assert response.json()["system_prompt"] == "Du bist der Buchhaltungs-Assistent."

    # Agent-Rollen ersetzen
    response = client.post(
        f"/api/admin/agents/{agent_id}/roles", headers=headers, json={"role_ids": [role_buha_id, it.id]}
    )
    assert response.status_code == 200
    assert set(response.json()["roles"]) == {"Buchhaltung", "IT"}

    # Agent deaktivieren
    response = client.patch(f"/api/admin/agents/{agent_id}", headers=headers, json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Benutzer deaktivieren
    user_id = response.json()["id"] if False else None
    users = client.get("/api/admin/users", headers=headers).json()
    new_user = next(u for u in users if u["email"] == "newuser@example.com")
    response = client.patch(
        f"/api/admin/users/{new_user['id']}", headers=headers, json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_cannot_deactivate_self(client, db):
    it = make_role(db, "IT")
    admin = make_user(db, "root@example.com", is_admin=True, roles=[it])
    headers = login(client, "root@example.com")
    response = client.patch(f"/api/admin/users/{admin.id}", headers=headers, json={"is_active": False})
    assert response.status_code == 400


def test_admin_agent_list_contains_system_prompt(client, db):
    """Admin darf die Konfiguration sehen; normale Nutzer bekommen sie nie (siehe test_agents)."""
    it = make_role(db, "IT")
    make_user(db, "admin2@example.com", is_admin=True, roles=[it])
    make_agent(db, "IT Support", "it-support", roles=[it], system_prompt="GEHEIM-PROMPT")
    headers = login(client, "admin2@example.com")
    response = client.get("/api/admin/agents", headers=headers)
    assert response.status_code == 200
    assert any(a["system_prompt"] == "GEHEIM-PROMPT" for a in response.json())
