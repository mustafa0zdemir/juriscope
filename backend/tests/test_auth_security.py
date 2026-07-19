from datetime import datetime, timedelta, timezone

from app.config.settings import settings
from app.core.security import hash_password
from app.models.user import User


def register_payload(**overrides):
    payload = {
        "username": "hukukcu",
        "email": "hukukcu@example.com",
        "full_name": "Hukuk Uzmanı",
        "password": "Guvenli!12345",
        "password_confirmation": "Guvenli!12345",
    }
    payload.update(overrides)
    return payload


def test_user_can_register(client, db):
    response = client.post("/api/v1/auth/register", json=register_payload())

    assert response.status_code == 201
    assert response.json()["user"]["username"] == "hukukcu"
    assert db.query(User).filter_by(username="hukukcu").one().is_admin is False


def test_registration_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json=register_payload(password="weak", password_confirmation="weak"),
    )

    assert response.status_code == 422


def test_registration_rejects_duplicate_email(client, db):
    db.add(
        User(
            username="existing",
            email="hukukcu@example.com",
            hashed_password=hash_password("Existing!12345"),
        )
    )
    db.commit()

    response = client.post("/api/v1/auth/register", json=register_payload())

    assert response.status_code == 409


def test_failed_logins_lock_account(client, db):
    user = User(
        username="lockeduser",
        email="locked@example.com",
        hashed_password=hash_password("Correct!12345"),
    )
    db.add(user)
    db.commit()

    for _ in range(settings.max_login_attempts):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "lockeduser", "password": "Wrong!12345"},
        )
        assert response.status_code == 401

    db.refresh(user)
    assert user.locked_until is not None
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "lockeduser", "password": "Correct!12345"},
    )
    assert response.status_code == 401


def test_expired_lock_is_cleared_after_successful_login(client, db):
    user = User(
        username="recovered",
        email="recovered@example.com",
        hashed_password=hash_password("Correct!12345"),
        failed_login_attempts=settings.max_login_attempts,
        locked_until=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1),
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "recovered@example.com", "password": "Correct!12345"},
    )

    assert response.status_code == 200
    db.refresh(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
