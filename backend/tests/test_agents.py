"""Kritische Berechtigungsfälle für Agent-Zugriff (Server-seitige Authorization)."""

from tests.conftest import login, make_agent, make_role, make_user


def _setup(db):
    it = make_role(db, "IT")
    logistik = make_role(db, "Logistik")
    it_user = make_user(db, "it-user@example.com", roles=[it])
    logistik_user = make_user(db, "logistik-user@example.com", roles=[logistik])
    it_agent = make_agent(db, "IT Support", "it-support", roles=[it])
    logistik_agent = make_agent(db, "Logistik", "logistik", roles=[logistik])
    return it_user, logistik_user, it_agent, logistik_agent


def test_unauthenticated_get_agents_401(client, db):
    response = client.get("/api/agents")
    assert response.status_code == 401


def test_user_sees_only_own_agents(client, db):
    it_user, logistik_user, it_agent, logistik_agent = _setup(db)

    headers = login(client, "it-user@example.com")
    response = client.get("/api/agents", headers=headers)
    assert response.status_code == 200
    slugs = [a["slug"] for a in response.json()]
    assert slugs == ["it-support"]

    headers = login(client, "logistik-user@example.com")
    response = client.get("/api/agents", headers=headers)
    assert response.status_code == 200
    slugs = [a["slug"] for a in response.json()]
    assert slugs == ["logistik"]


def test_agent_detail_allowed_200(client, db):
    it_user, logistik_user, it_agent, logistik_agent = _setup(db)
    headers = login(client, "it-user@example.com")
    response = client.get(f"/api/agents/{it_agent.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "IT Support"


def test_agent_detail_forbidden_403(client, db):
    """User ohne Berechtigung darf fremden Agent NICHT über direkte API-Anfrage erreichen."""
    it_user, logistik_user, it_agent, logistik_agent = _setup(db)
    headers = login(client, "it-user@example.com")
    response = client.get(f"/api/agents/{logistik_agent.id}", headers=headers)
    assert response.status_code == 403


def test_agent_not_found_404(client, db):
    it = make_role(db, "IT")
    make_user(db, "x@example.com", roles=[it])
    headers = login(client, "x@example.com")
    response = client.get("/api/agents/99999", headers=headers)
    assert response.status_code == 404


def test_inactive_agent_403(client, db):
    """Deaktivierter Agent: kein Zugriff, auch mit passender Rolle."""
    it = make_role(db, "IT")
    user = make_user(db, "y@example.com", roles=[it])
    agent = make_agent(db, "Alter Agent", "alter-agent", roles=[it], is_active=False)
    headers = login(client, "y@example.com")
    response = client.get(f"/api/agents/{agent.id}", headers=headers)
    assert response.status_code == 403

    # Auch nicht in der Liste
    response = client.get("/api/agents", headers=headers)
    assert response.json() == []


def test_session_creation_forbidden_for_foreign_agent(client, db):
    it_user, logistik_user, it_agent, logistik_agent = _setup(db)
    headers = login(client, "it-user@example.com")
    response = client.post(f"/api/agents/{logistik_agent.id}/sessions", headers=headers)
    assert response.status_code == 403


def test_agent_detail_never_leaks_system_prompt(client, db):
    """Keine Ausgabe von System-Prompts an normale Benutzer."""
    it_user, logistik_user, it_agent, logistik_agent = _setup(db)
    headers = login(client, "it-user@example.com")
    for path in ("/api/agents", f"/api/agents/{it_agent.id}"):
        response = client.get(path if path == "/api/agents" else path, headers=headers)
        body = response.json()
        text = str(body)
        assert "SEHR GEHEIMER SYSTEM-PROMPT" not in text
        if isinstance(body, dict):
            assert "system_prompt" not in body
            assert "model_id" not in body
