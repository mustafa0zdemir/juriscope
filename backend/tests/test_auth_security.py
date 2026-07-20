from datetime import datetime, timedelta, timezone

from app.config.settings import settings
from app.core.rate_limit import auth_rate_limiter
from app.core.security import hash_password
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.user_session import UserSession


def setup_function():
    auth_rate_limiter.clear()


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


def test_login_returns_refresh_token_and_records_session(client, db):
    user = User(
        username="sessionuser",
        email="session@example.com",
        hashed_password=hash_password("Correct!12345"),
    )
    db.add(user)
    db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "sessionuser", "password": "Correct!12345"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]
    assert db.query(UserSession).filter_by(user_id=user.id).count() == 1
    assert db.query(AuditLog).filter_by(event_type="auth.login", outcome="success").count() == 1


def test_refresh_token_is_rotated(client, db):
    user = User(
        username="refreshuser",
        email="refresh@example.com",
        hashed_password=hash_password("Correct!12345"),
    )
    db.add(user)
    db.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "refreshuser", "password": "Correct!12345"},
    ).json()

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["refresh_token"] != login["refresh_token"]
    assert db.query(UserSession).filter_by(user_id=user.id, revoked_at=None).count() == 1

    replay = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert replay.status_code == 401


def test_change_password_revokes_all_sessions(client, db, current_user):
    current_user.hashed_password = hash_password("Current!12345")
    db.commit()
    session = UserSession(
        id="f105be16-7f39-4a4c-95ba-b2ad60c4ef66",
        user_id=current_user.id,
        refresh_token_hash="x" * 64,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1),
    )
    db.add(session)
    db.commit()

    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "Current!12345",
            "new_password": "Changed!12345",
            "new_password_confirmation": "Changed!12345",
        },
    )

    assert response.status_code == 200
    db.refresh(session)
    assert session.revoked_at is not None


def test_security_headers_are_present(client):
    response = client.get("/api/v1/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


def test_cache_health_reports_disabled_redis(client):
    response = client.get("/api/v1/health/cache")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "redis",
        "enabled": False,
        "status": "disabled",
    }
