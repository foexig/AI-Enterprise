"""Chat-API: Session-Isolation, TTL, Rollenprüfung zur Laufzeit."""

from tests.conftest import login, make_agent, make_role, make_session, make_user


def _setup(db):
    it = make_role(db, "IT")
    logistik = make_role(db, "Logistik")
    user_a = make_user(db, "a@example.com", roles=[it])
    user_b = make_user(db, "b@example.com", roles=[logistik])
    agent = make_agent(db, "IT Support", "it-support", roles=[it])
    return it, logistik, user_a, user_b, agent


def test_send_message_and_get_answer(client, db):
    it, logistik, user_a, user_b, agent = _setup(db)
    headers = login(client, "a@example.com")
    session = client.post(f"/api/agents/{agent.id}/sessions", headers=headers)
    assert session.status_code == 201
    session_id = session.json()["id"]

    response = client.post(
        f"/api/sessions/{session_id}/messages",
        headers=headers,
        json={"content": "Wie ist der Status von Auftrag 4711?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["message"]["role"] == "assistant"
    assert body["message"]["content"]
    assert "model_id" in body
    assert body["input_tokens"] >= 0 and body["output_tokens"] >= 0

    # Nachricht erscheint in der Historie
    history = client.get(f"/api/sessions/{session_id}/messages", headers=headers)
    assert history.status_code == 200
    roles = [m["role"] for m in history.json()]
    assert roles == ["user", "assistant"]


def test_foreign_session_id_404(client, db):
    """User kann fremde Session-ID nicht verwenden."""
    it, logistik, user_a, user_b, agent = _setup(db)
    headers_a = login(client, "a@example.com")
    headers_b = login(client, "b@example.com")
    session = client.post(f"/api/agents/{agent.id}/sessions", headers=headers_a)
    session_id = session.json()["id"]

    # Anderer Benutzer (gar keine Rolle für den Agent): 404, Existenz wird nicht aufgedeckt
    assert client.get(f"/api/sessions/{session_id}/messages", headers=headers_b).status_code == 404
    response = client.post(
        f"/api/sessions/{session_id}/messages", headers=headers_b, json={"content": "Hallo"}
    )
    assert response.status_code == 404


def test_expired_session_403(client, db):
    """Abgelaufene Session (TTL) darf nicht mehr als Kontext verwendet werden."""
    it, logistik, user_a, user_b, agent = _setup(db)
    headers = login(client, "a@example.com")
    session = make_session(db, user_a, agent, expired=True)
    response = client.post(
        f"/api/sessions/{session.id}/messages", headers=headers, json={"content": "Hallo"}
    )
    assert response.status_code == 403
    assert "abgelaufen" in response.json()["detail"].lower() or "Session" in response.json()["detail"]


def test_role_removed_mid_conversation_403(client, db):
    """User verliert die Rolle während einer laufenden Session -> kein Senden mehr möglich."""
    it, logistik, user_a, user_b, agent = _setup(db)
    headers = login(client, "a@example.com")
    session = make_session(db, user_a, agent)
    user_a.roles = [logistik]
    db.commit()
    response = client.post(
        f"/api/sessions/{session.id}/messages", headers=headers, json={"content": "Hallo"}
    )
    assert response.status_code == 403


def test_agent_deactivated_mid_conversation_403(client, db):
    it, logistik, user_a, user_b, agent = _setup(db)
    headers = login(client, "a@example.com")
    session = make_session(db, user_a, agent)
    agent.is_active = False
    db.commit()
    response = client.post(
        f"/api/sessions/{session.id}/messages", headers=headers, json={"content": "Hallo"}
    )
    assert response.status_code == 403


def test_sessions_isolated_between_users(client, db):
    """Zwei verschiedene Agents desselben Users haben getrennte Kontexte."""
    it, logistik, user_a, user_b, agent = _setup(db)
    agent2 = make_agent(db, "Softwareentwicklung", "softwareentwicklung", roles=[it])
    headers = login(client, "a@example.com")

    s1 = client.post(f"/api/agents/{agent.id}/sessions", headers=headers).json()["id"]
    s2 = client.post(f"/api/agents/{agent2.id}/sessions", headers=headers).json()["id"]

    client.post(f"/api/sessions/{s1}/messages", headers=headers, json={"content": "IT-Frage"})

    # Session 2 kennt die Nachricht aus Session 1 nicht
    messages_s2 = client.get(f"/api/sessions/{s2}/messages", headers=headers).json()
    assert messages_s2 == []


def test_empty_message_rejected(client, db):
    it, logistik, user_a, user_b, agent = _setup(db)
    headers = login(client, "a@example.com")
    session = make_session(db, user_a, agent)
    response = client.post(
        f"/api/sessions/{session.id}/messages", headers=headers, json={"content": ""}
    )
    assert response.status_code == 422
