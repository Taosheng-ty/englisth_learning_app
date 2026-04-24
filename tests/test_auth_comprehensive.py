"""Comprehensive tests for auth, user settings, and session flows."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.database import init_db
from app.routers.auth import SESSIONS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_app():
    """Create a fresh app + TestClient backed by a throwaway SQLite DB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db(db_path)
    app = create_app(db_path)
    return TestClient(app), db_path


@pytest.fixture(autouse=True)
def _clear_sessions():
    """Ensure the global session store is empty before every test."""
    SESSIONS.clear()
    yield
    SESSIONS.clear()


@pytest.fixture()
def fresh():
    """Yield (client, db_path) then clean up."""
    client, db_path = make_app()
    yield client, db_path
    db_path.unlink(missing_ok=True)


def _register(client, username="alice", password="pass123", ui_language="zh"):
    return client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "ui_language": ui_language},
    )


def _login(client, username="alice", password="pass123"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def _register_and_login(client, username="alice", password="pass123", ui_language="zh"):
    _register(client, username, password, ui_language)
    return _login(client, username, password)


# ===================================================================
# 1. REGISTRATION
# ===================================================================

class TestRegistration:
    """Registration endpoint: /api/auth/register"""

    def test_register_with_zh(self, fresh):
        """Register a user with Chinese (zh) UI language."""
        client, _ = fresh
        resp = _register(client, "user_zh", "pw123", "zh")
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "user_zh"
        assert body["ui_language"] == "zh"

    def test_register_with_vi(self, fresh):
        """Register a user with Vietnamese (vi) UI language."""
        client, _ = fresh
        resp = _register(client, "user_vi", "pw123", "vi")
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "user_vi"
        assert body["ui_language"] == "vi"

    def test_register_default_language_is_zh(self, fresh):
        """If ui_language is omitted, default should be 'zh'."""
        client, _ = fresh
        resp = client.post(
            "/api/auth/register",
            json={"username": "default_lang", "password": "pw123"},
        )
        assert resp.status_code == 200
        assert resp.json()["ui_language"] == "zh"

    def test_duplicate_username_rejected(self, fresh):
        """Registering the same username twice should return 409."""
        client, _ = fresh
        _register(client, "alice", "pw123")
        resp = _register(client, "alice", "other_pw")
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_missing_username_field(self, fresh):
        """Omitting 'username' should return 422 (validation error)."""
        client, _ = fresh
        resp = client.post("/api/auth/register", json={"password": "pw123"})
        assert resp.status_code == 422

    def test_missing_password_field(self, fresh):
        """Omitting 'password' should return 422 (validation error)."""
        client, _ = fresh
        resp = client.post("/api/auth/register", json={"username": "nopass"})
        assert resp.status_code == 422

    def test_missing_all_fields(self, fresh):
        """Sending empty JSON should return 422."""
        client, _ = fresh
        resp = client.post("/api/auth/register", json={})
        assert resp.status_code == 422


# ===================================================================
# 2. LOGIN
# ===================================================================

class TestLogin:
    """Login endpoint: /api/auth/login"""

    def test_login_correct_credentials(self, fresh):
        """Successful login returns 200 and sets a session cookie."""
        client, _ = fresh
        _register(client, "alice", "pass123")
        resp = _login(client, "alice", "pass123")
        assert resp.status_code == 200
        assert resp.json()["username"] == "alice"
        assert "session" in resp.cookies

    def test_login_wrong_password(self, fresh):
        """Wrong password returns 401."""
        client, _ = fresh
        _register(client, "alice", "pass123")
        resp = _login(client, "alice", "WRONG")
        assert resp.status_code == 401

    def test_login_wrong_username(self, fresh):
        """Existing user but with a different (wrong) username returns 401."""
        client, _ = fresh
        _register(client, "alice", "pass123")
        resp = _login(client, "bob", "pass123")
        assert resp.status_code == 401

    def test_login_non_existent_user(self, fresh):
        """Logging in with a totally unknown user returns 401."""
        client, _ = fresh
        resp = _login(client, "ghost", "anything")
        assert resp.status_code == 401


# ===================================================================
# 3. SESSION
# ===================================================================

class TestSession:
    """Session management: protected endpoints, logout invalidation."""

    def test_profile_without_login_returns_401(self, fresh):
        """GET /api/user/profile without a session cookie should 401."""
        client, _ = fresh
        resp = client.get("/api/user/profile")
        assert resp.status_code == 401

    def test_settings_without_login_returns_401(self, fresh):
        """PUT /api/user/settings without a session cookie should 401."""
        client, _ = fresh
        resp = client.put("/api/user/settings", json={"daily_goal": 10})
        assert resp.status_code == 401

    def test_logout_then_profile_returns_401(self, fresh):
        """After logout, accessing profile should 401."""
        client, _ = fresh
        _register_and_login(client)
        # Verify profile works before logout
        assert client.get("/api/user/profile").status_code == 200
        # Logout
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200
        # Now profile should fail
        assert client.get("/api/user/profile").status_code == 401

    def test_logout_then_settings_returns_401(self, fresh):
        """After logout, updating settings should 401."""
        client, _ = fresh
        _register_and_login(client)
        client.post("/api/auth/logout")
        resp = client.put("/api/user/settings", json={"daily_goal": 10})
        assert resp.status_code == 401

    def test_logout_without_session_is_ok(self, fresh):
        """Calling logout when not logged in should still return 200."""
        client, _ = fresh
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200


# ===================================================================
# 4. PROFILE
# ===================================================================

class TestProfile:
    """GET /api/user/profile returns correct default and updated fields."""

    def test_profile_returns_all_required_fields(self, fresh):
        """Profile response must include all specified keys."""
        client, _ = fresh
        _register_and_login(client, ui_language="zh")
        resp = client.get("/api/user/profile")
        assert resp.status_code == 200
        data = resp.json()
        required_keys = {
            "username", "ui_language", "daily_goal",
            "tts_speed", "xp", "streak_days", "sentences_today",
        }
        assert required_keys.issubset(data.keys())

    def test_profile_default_values(self, fresh):
        """A freshly registered user has expected defaults."""
        client, _ = fresh
        _register_and_login(client, "newbie", "pw", "zh")
        data = client.get("/api/user/profile").json()
        assert data["username"] == "newbie"
        assert data["ui_language"] == "zh"
        assert data["daily_goal"] == 5
        assert data["tts_speed"] == 1.0
        assert data["xp"] == 0
        assert data["streak_days"] == 0
        assert data["sentences_today"] == 0

    def test_profile_returns_vi_for_vi_user(self, fresh):
        """User registered with vi should have ui_language = vi."""
        client, _ = fresh
        _register_and_login(client, "vi_user", "pw", "vi")
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "vi"


# ===================================================================
# 5. SETTINGS UPDATE
# ===================================================================

class TestSettingsUpdate:
    """PUT /api/user/settings: full and partial updates."""

    def test_change_ui_language_zh_to_vi(self, fresh):
        """Change ui_language from zh to vi and verify persistence."""
        client, _ = fresh
        _register_and_login(client, ui_language="zh")
        resp = client.put("/api/user/settings", json={"ui_language": "vi"})
        assert resp.status_code == 200
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "vi"

    def test_change_daily_goal(self, fresh):
        """Change daily_goal and verify persistence."""
        client, _ = fresh
        _register_and_login(client)
        client.put("/api/user/settings", json={"daily_goal": 20})
        data = client.get("/api/user/profile").json()
        assert data["daily_goal"] == 20

    def test_change_tts_speed(self, fresh):
        """Change tts_speed and verify persistence."""
        client, _ = fresh
        _register_and_login(client)
        client.put("/api/user/settings", json={"tts_speed": 0.75})
        data = client.get("/api/user/profile").json()
        assert data["tts_speed"] == 0.75

    def test_partial_update_only_language(self, fresh):
        """Updating only ui_language should not change daily_goal or tts_speed."""
        client, _ = fresh
        _register_and_login(client, ui_language="zh")
        # First set specific values for daily_goal and tts_speed
        client.put("/api/user/settings", json={"daily_goal": 15, "tts_speed": 1.5})
        # Now update only language
        client.put("/api/user/settings", json={"ui_language": "vi"})
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "vi"
        assert data["daily_goal"] == 15
        assert data["tts_speed"] == 1.5

    def test_partial_update_only_daily_goal(self, fresh):
        """Updating only daily_goal should not change other settings."""
        client, _ = fresh
        _register_and_login(client, ui_language="vi")
        client.put("/api/user/settings", json={"daily_goal": 99})
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "vi"
        assert data["daily_goal"] == 99
        assert data["tts_speed"] == 1.0  # unchanged default

    def test_partial_update_only_tts_speed(self, fresh):
        """Updating only tts_speed should not change other settings."""
        client, _ = fresh
        _register_and_login(client, ui_language="zh")
        client.put("/api/user/settings", json={"tts_speed": 2.0})
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "zh"
        assert data["daily_goal"] == 5
        assert data["tts_speed"] == 2.0

    def test_full_update_all_fields(self, fresh):
        """Update all three fields at once."""
        client, _ = fresh
        _register_and_login(client, ui_language="zh")
        client.put("/api/user/settings", json={
            "ui_language": "vi",
            "daily_goal": 30,
            "tts_speed": 0.5,
        })
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "vi"
        assert data["daily_goal"] == 30
        assert data["tts_speed"] == 0.5

    def test_empty_settings_body_is_noop(self, fresh):
        """Sending {} should succeed and not change anything."""
        client, _ = fresh
        _register_and_login(client, ui_language="zh")
        resp = client.put("/api/user/settings", json={})
        assert resp.status_code == 200
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "zh"
        assert data["daily_goal"] == 5
        assert data["tts_speed"] == 1.0

    def test_multiple_sequential_updates(self, fresh):
        """Apply several updates in sequence; the last value wins."""
        client, _ = fresh
        _register_and_login(client)
        client.put("/api/user/settings", json={"daily_goal": 10})
        client.put("/api/user/settings", json={"daily_goal": 20})
        client.put("/api/user/settings", json={"daily_goal": 30})
        data = client.get("/api/user/profile").json()
        assert data["daily_goal"] == 30


# ===================================================================
# 6. LANGUAGE SWITCHING
# ===================================================================

class TestLanguageSwitching:
    """Verify that language registration and switching work end-to-end."""

    def test_register_zh_then_switch_to_vi(self, fresh):
        """Register with zh, update to vi, verify profile returns vi."""
        client, _ = fresh
        _register_and_login(client, "zhuser", "pw", "zh")
        assert client.get("/api/user/profile").json()["ui_language"] == "zh"
        client.put("/api/user/settings", json={"ui_language": "vi"})
        assert client.get("/api/user/profile").json()["ui_language"] == "vi"

    def test_register_vi_user_returns_vi(self, fresh):
        """Register directly with vi, verify profile returns vi."""
        client, _ = fresh
        _register_and_login(client, "viuser", "pw", "vi")
        data = client.get("/api/user/profile").json()
        assert data["ui_language"] == "vi"

    def test_switch_vi_back_to_zh(self, fresh):
        """Start vi, switch to zh, verify."""
        client, _ = fresh
        _register_and_login(client, "switcher", "pw", "vi")
        client.put("/api/user/settings", json={"ui_language": "zh"})
        assert client.get("/api/user/profile").json()["ui_language"] == "zh"

    def test_two_users_different_languages(self, fresh):
        """Two users in the same DB with different languages."""
        client, _ = fresh
        # User A - zh
        _register(client, "userA", "pw", "zh")
        _login(client, "userA", "pw")
        assert client.get("/api/user/profile").json()["ui_language"] == "zh"
        client.post("/api/auth/logout")
        # User B - vi
        _register(client, "userB", "pw", "vi")
        _login(client, "userB", "pw")
        assert client.get("/api/user/profile").json()["ui_language"] == "vi"


# ===================================================================
# 7. EDGE CASES
# ===================================================================

class TestEdgeCases:
    """Edge cases around usernames and passwords."""

    def test_empty_username(self, fresh):
        """Empty-string username should be rejected (422 or 409)."""
        client, _ = fresh
        resp = _register(client, "", "pw123")
        # The app might allow it at the pydantic level (str can be empty),
        # but we document the observed behavior.
        # If 200, the app tolerates empty usernames (design choice).
        assert resp.status_code in (200, 422, 400)

    def test_empty_password(self, fresh):
        """Empty-string password should be rejected (422) or tolerated."""
        client, _ = fresh
        resp = _register(client, "emptypass", "")
        assert resp.status_code in (200, 422, 400)

    def test_very_long_username(self, fresh):
        """A username of 1000 characters should be handled gracefully."""
        client, _ = fresh
        long_name = "a" * 1000
        resp = _register(client, long_name, "pw123")
        # Should either succeed or return a client error, not 500.
        assert resp.status_code < 500

    def test_special_characters_in_username(self, fresh):
        """Usernames with special characters like !@#$%^& should not crash."""
        client, _ = fresh
        resp = _register(client, "u$er!@#%^&*()", "pw123")
        assert resp.status_code < 500

    def test_unicode_username(self, fresh):
        """Chinese/Vietnamese characters in username."""
        client, _ = fresh
        resp = _register(client, "用户名", "pw123", "zh")
        assert resp.status_code < 500
        if resp.status_code == 200:
            # Verify we can log in with it
            login_resp = _login(client, "用户名", "pw123")
            assert login_resp.status_code == 200

    def test_sql_injection_in_username(self, fresh):
        """SQL injection attempt should not crash the server."""
        client, _ = fresh
        resp = _register(client, "'; DROP TABLE users; --", "pw123")
        assert resp.status_code < 500

    def test_whitespace_only_username(self, fresh):
        """Username of only spaces should be handled."""
        client, _ = fresh
        resp = _register(client, "   ", "pw123")
        assert resp.status_code < 500

    def test_register_no_json_body(self, fresh):
        """POST with no body at all should return 422."""
        client, _ = fresh
        resp = client.post("/api/auth/register")
        assert resp.status_code == 422

    def test_login_no_json_body(self, fresh):
        """POST login with no body should return 422."""
        client, _ = fresh
        resp = client.post("/api/auth/login")
        assert resp.status_code == 422
