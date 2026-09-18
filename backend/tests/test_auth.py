from app.models import User
from tests.conftest import login, make_role, make_user


def test_login_success(client, db):
    make_user(db, "alice@example.com")
    response = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "password123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"


def test_login_wrong_password(client, db):
    make_user(db, "bob@example.com")
    response = client.post("/api/auth/login", json={"email": "bob@example.com", "password": "wrongpassword"})
    assert response.status_code == 401


def test_login_unknown_email(client, db):
    response = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "password123"})
    assert response.status_code == 401


def test_login_deactivated_user_forbidden(client, db):
    role = make_role(db, "IT")
    user = make_user(db, "carol@example.com", roles=[role])
    user.is_active = False
    db.commit()
    response = client.post("/api/auth/login", json={"email": "carol@example.com", "password": "password123"})
    assert response.status_code == 403


def test_me_requires_auth(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_roles(client, db):
    role = make_role(db, "IT")
    make_user(db, "dave@example.com", roles=[role])
    headers = login(client, "dave@example.com")
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["roles"] == ["IT"]
    assert "password_hash" not in response.json()


def test_password_not_stored_plaintext(client, db):
    make_user(db, "eve@example.com")
    user = db.query(User).filter_by(email="eve@example.com").first()
    assert user.password_hash != "password123"
    assert user.password_hash.startswith("$2")
