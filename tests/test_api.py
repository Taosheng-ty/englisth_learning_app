import json
import sqlite3
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.database import init_db, get_db_connection


def test_init_db_creates_tables():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    db_path.unlink()
    assert "users" in tables
    assert "lessons" in tables
    assert "sentences" in tables
    assert "user_progress" in tables
    assert "vocabulary" in tables


def test_get_db_connection():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db(db_path)
    conn = get_db_connection(db_path)
    assert conn is not None
    conn.close()
    db_path.unlink()


def _make_app():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db(db_path)
    app = create_app(db_path)
    return TestClient(app), db_path


def _seed_lesson(db_path):
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "Greetings", "问候", "Chao hoi", "A1", "daily_conversation", 2),
    )
    words = [
        {"word": "Hello", "ipa": "/həˈloʊ/", "pos": "interjection", "pos_zh": "感叹词", "pos_vi": "than tu",
         "role": "greeting", "role_zh": "问候语", "role_vi": "loi chao", "group": 0, "group_color": "#795548"},
    ]
    constituents = [
        {"group": 0, "label_en": "greeting", "label_zh": "问候语", "label_vi": "loi chao", "word_indices": [0], "color": "#795548"},
    ]
    conn.execute(
        "INSERT INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("1-01", 1, 1, "Hello", "你好", "Xin chao", json.dumps(words), json.dumps(constituents)),
    )
    conn.execute(
        "INSERT INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("1-02", 1, 2, "Goodbye", "再见", "Tam biet", json.dumps(words), json.dumps(constituents)),
    )
    conn.commit()
    conn.close()


def test_register_and_login():
    client, db_path = _make_app()
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice"
    resp = client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    assert resp.status_code == 200
    assert "session" in resp.cookies
    db_path.unlink()


def test_register_duplicate():
    client, db_path = _make_app()
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    resp = client.post("/api/auth/register", json={"username": "alice", "password": "other"})
    assert resp.status_code == 409
    db_path.unlink()


def test_login_wrong_password():
    client, db_path = _make_app()
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    resp = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401
    db_path.unlink()


def test_logout():
    client, db_path = _make_app()
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    db_path.unlink()


def test_list_lessons():
    client, db_path = _make_app()
    _seed_lesson(db_path)
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    resp = client.get("/api/lessons")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["title"] == "Greetings"
    db_path.unlink()


def test_get_lesson_detail():
    client, db_path = _make_app()
    _seed_lesson(db_path)
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    resp = client.get("/api/lessons/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert len(data["sentences"]) == 2
    db_path.unlink()


def test_get_sentence():
    client, db_path = _make_app()
    _seed_lesson(db_path)
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    resp = client.get("/api/lessons/1/sentences/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["text"] == "Hello"
    assert len(data["words"]) == 1
    db_path.unlink()


def _auth_client_with_lesson():
    client, db_path = _make_app()
    _seed_lesson(db_path)
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123"})
    client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    return client, db_path


def test_submit_dictation():
    client, db_path = _auth_client_with_lesson()
    resp = client.post("/api/practice/submit", json={"sentence_id": "1-01", "typed_text": "Hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 1.0
    assert data["xp_earned"] == 10
    db_path.unlink()


def test_submit_dictation_wrong():
    client, db_path = _auth_client_with_lesson()
    resp = client.post("/api/practice/submit", json={"sentence_id": "1-01", "typed_text": "Goodbye"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] < 1.0
    db_path.unlink()


def test_self_rate():
    client, db_path = _auth_client_with_lesson()
    resp = client.post("/api/practice/self-rate", json={"sentence_id": "1-01", "rating": "good"})
    assert resp.status_code == 200
    db_path.unlink()


def test_get_stats():
    client, db_path = _auth_client_with_lesson()
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "xp" in data
    assert "streak_days" in data
    db_path.unlink()


def test_get_review_due():
    client, db_path = _auth_client_with_lesson()
    resp = client.get("/api/review/due")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    db_path.unlink()


def test_vocabulary_empty():
    client, db_path = _auth_client_with_lesson()
    resp = client.get("/api/vocabulary")
    assert resp.status_code == 200
    assert resp.json() == []
    db_path.unlink()


def test_vocabulary_after_practice():
    client, db_path = _auth_client_with_lesson()
    client.post("/api/practice/submit", json={"sentence_id": "1-01", "typed_text": "Hello"})
    resp = client.get("/api/vocabulary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["word"] == "hello"
    db_path.unlink()


def test_vocabulary_flashcards():
    client, db_path = _auth_client_with_lesson()
    client.post("/api/practice/submit", json={"sentence_id": "1-01", "typed_text": "Hello"})
    resp = client.get("/api/vocabulary/flashcards")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "word" in data[0]
    assert "ipa" in data[0]
    db_path.unlink()


def test_get_profile():
    client, db_path = _auth_client_with_lesson()
    resp = client.get("/api/user/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "alice"
    assert data["ui_language"] == "zh"
    db_path.unlink()


def test_update_settings():
    client, db_path = _auth_client_with_lesson()
    resp = client.put("/api/user/settings", json={"ui_language": "vi", "daily_goal": 10, "tts_speed": 1.5})
    assert resp.status_code == 200
    resp = client.get("/api/user/profile")
    data = resp.json()
    assert data["ui_language"] == "vi"
    assert data["daily_goal"] == 10
    assert data["tts_speed"] == 1.5
    db_path.unlink()
