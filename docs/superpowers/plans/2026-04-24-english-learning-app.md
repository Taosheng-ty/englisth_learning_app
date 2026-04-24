# English Learning App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete English learning webapp with rich sentence annotations, TTS, dictation practice, and spaced repetition for Chinese/Vietnamese learners.

**Architecture:** Python FastAPI serves a REST API backed by SQLite. The frontend is a vanilla JS SPA served as static files. Lesson content is pre-computed and stored as JSON in the database. The browser handles TTS via the Web Speech API and renders sentence annotations with flexbox + SVG.

**Tech Stack:** Python 3.10+, FastAPI, SQLite, uvicorn, bcrypt, vanilla JS, CSS3 flexbox, Web Speech API, jsdiff

---

## File Map

```
englisht_turorial/
├── app/
│   ├── main.py              — FastAPI app, mounts routers + static files
│   ├── config.py            — Settings (DB path, secret key, session expiry)
│   ├── database.py          — SQLite init, get_db helper, schema creation
│   ├── models.py            — Pydantic request/response models
│   ├── routers/
│   │   ├── auth.py          — POST /api/auth/register, login, logout
│   │   ├── lessons.py       — GET /api/lessons, /api/lessons/{id}, /api/lessons/{id}/sentences/{index}
│   │   ├── practice.py      — POST /api/practice/submit, /api/practice/self-rate; GET /api/review/due, /api/stats
│   │   └── vocabulary.py    — GET /api/vocabulary, /api/vocabulary/flashcards
│   ├── services/
│   │   ├── scoring.py       — Levenshtein distance, word diff, score calculation
│   │   └── spaced_rep.py    — Leitner bucket logic, next review date
│   └── static/
│       ├── index.html       — SPA shell with all page containers
│       ├── css/
│       │   └── style.css    — All styles (global, dashboard, lesson, vocab, settings)
│       └── js/
│           ├── app.js       — SPA router, auth state, API helpers, page init
│           ├── i18n.js      — Chinese/Vietnamese UI translation strings
│           ├── tts.js       — Web Speech API: speak, highlight, speed, repeat
│           ├── annotation.js — Render word annotations + SVG constituent brackets
│           └── dictation.js — Typing input, IME handling, diff display, scoring
├── data/
│   └── lessons/
│       ├── lesson_001.json  — Starter lesson: Greetings (A1)
│       ├── lesson_002.json  — Starter lesson: Daily Routines (A1)
│       └── lesson_003.json  — Starter lesson: At the Restaurant (A1)
├── tools/
│   └── import_lessons.py    — Load JSON lesson files into SQLite
├── tests/
│   ├── test_scoring.py      — Unit tests for scoring service
│   ├── test_spaced_rep.py   — Unit tests for spaced repetition
│   └── test_api.py          — Integration tests for API endpoints
└── requirements.txt
```

---

### Task 1: Project Scaffolding and Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `app/config.py`
- Create: `app/__init__.py`
- Create: `app/routers/__init__.py`
- Create: `app/services/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
bcrypt==4.2.0
python-multipart==0.0.9
```

- [ ] **Step 2: Create app/config.py**

```python
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "english_learning.db"
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
SESSION_EXPIRY_HOURS = 24
```

- [ ] **Step 3: Create empty __init__.py files**

Create empty files at:
- `app/__init__.py`
- `app/routers/__init__.py`
- `app/services/__init__.py`
- `tests/__init__.py`

- [ ] **Step 4: Create directory structure**

```bash
mkdir -p app/routers app/services app/static/css app/static/js data/lessons tools tests
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

- [ ] **Step 6: Commit**

```bash
git add requirements.txt app/config.py app/__init__.py app/routers/__init__.py app/services/__init__.py tests/__init__.py
git commit -m "feat: scaffold project structure and dependencies"
```

---

### Task 2: Database Layer

**Files:**
- Create: `app/database.py`
- Test: `tests/test_api.py` (initial setup)

- [ ] **Step 1: Write test for database initialization**

Create `tests/test_api.py`:

```python
import sqlite3
import tempfile
from pathlib import Path
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /fsx-neo/dedicated-fsx-data-repo-neo-us-east-1/toyng/toyng_ws/projects/Personalized_Product_search/englisht_turorial
python -m pytest tests/test_api.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.database'`

- [ ] **Step 3: Implement database.py**

Create `app/database.py`:

```python
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    ui_language TEXT NOT NULL DEFAULT 'zh',
    daily_goal INTEGER NOT NULL DEFAULT 5,
    tts_speed REAL NOT NULL DEFAULT 1.0,
    xp INTEGER NOT NULL DEFAULT 0,
    streak_days INTEGER NOT NULL DEFAULT 0,
    last_practice_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lessons (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    title_zh TEXT NOT NULL,
    title_vi TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    category TEXT NOT NULL,
    sentence_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sentences (
    id TEXT PRIMARY KEY,
    lesson_id INTEGER NOT NULL REFERENCES lessons(id),
    idx INTEGER NOT NULL,
    text TEXT NOT NULL,
    translation_zh TEXT NOT NULL,
    translation_vi TEXT NOT NULL,
    words_json TEXT NOT NULL,
    constituents_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    sentence_id TEXT NOT NULL REFERENCES sentences(id),
    mode TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 0.0,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt TIMESTAMP,
    next_review TIMESTAMP,
    leitner_bucket INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, sentence_id, mode)
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    word TEXT NOT NULL,
    ipa TEXT,
    pos TEXT,
    seen_count INTEGER NOT NULL DEFAULT 0,
    correct_count INTEGER NOT NULL DEFAULT 0,
    next_review TIMESTAMP,
    UNIQUE(user_id, word)
);
"""


def init_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
```

- [ ] **Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_api.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add app/database.py tests/test_api.py
git commit -m "feat: add SQLite database layer with schema"
```

---

### Task 3: Pydantic Models

**Files:**
- Create: `app/models.py`

- [ ] **Step 1: Create models.py**

```python
from pydantic import BaseModel
from typing import Optional


class RegisterRequest(BaseModel):
    username: str
    password: str
    ui_language: str = "zh"


class LoginRequest(BaseModel):
    username: str
    password: str


class SettingsUpdate(BaseModel):
    ui_language: Optional[str] = None
    daily_goal: Optional[int] = None
    tts_speed: Optional[float] = None


class DictationSubmit(BaseModel):
    sentence_id: str
    typed_text: str


class SelfRateRequest(BaseModel):
    sentence_id: str
    rating: str  # "good", "okay", "again"


class WordDiff(BaseModel):
    word: str
    status: str  # "correct", "incorrect", "missing", "extra", "close"
    expected: Optional[str] = None


class DictationResult(BaseModel):
    score: float
    xp_earned: int
    diffs: list[WordDiff]
    expected_text: str


class UserProfile(BaseModel):
    username: str
    ui_language: str
    daily_goal: int
    tts_speed: float
    xp: int
    streak_days: int
    sentences_today: int


class LessonSummary(BaseModel):
    id: int
    title: str
    title_zh: str
    title_vi: str
    difficulty: str
    category: str
    sentence_count: int
    completed_count: int


class WordAnnotation(BaseModel):
    word: str
    ipa: str
    pos: str
    pos_zh: str
    pos_vi: str
    role: str
    role_zh: str
    role_vi: str
    group: int
    group_color: str


class Constituent(BaseModel):
    group: int
    label_en: str
    label_zh: str
    label_vi: str
    word_indices: list[int]
    color: str


class SentenceDetail(BaseModel):
    id: str
    lesson_id: int
    index: int
    text: str
    translation_zh: str
    translation_vi: str
    words: list[WordAnnotation]
    constituents: list[Constituent]


class VocabEntry(BaseModel):
    word: str
    ipa: str
    pos: str
    seen_count: int
    correct_count: int
    status: str  # "mastered", "learning", "weak"


class StatsResponse(BaseModel):
    xp: int
    streak_days: int
    total_sentences_practiced: int
    total_words_learned: int
    accuracy_percent: float
    sentences_today: int
    daily_goal: int
```

- [ ] **Step 2: Verify models load**

```bash
python -c "from app.models import RegisterRequest, DictationResult, SentenceDetail; print('Models OK')"
```

Expected: `Models OK`

- [ ] **Step 3: Commit**

```bash
git add app/models.py
git commit -m "feat: add Pydantic request/response models"
```

---

### Task 4: Scoring Service

**Files:**
- Create: `app/services/scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Write scoring tests**

Create `tests/test_scoring.py`:

```python
from app.services.scoring import levenshtein, score_dictation


def test_levenshtein_identical():
    assert levenshtein("hello", "hello") == 0


def test_levenshtein_one_char():
    assert levenshtein("hello", "helo") == 1


def test_levenshtein_completely_different():
    assert levenshtein("abc", "xyz") == 3


def test_score_dictation_perfect():
    result = score_dictation("Yes I have to leave immediately", "yes i have to leave immediately")
    assert result["score"] == 1.0
    assert all(d["status"] == "correct" for d in result["diffs"])


def test_score_dictation_one_typo():
    result = score_dictation("Yes I have to leave immediately", "yes i have to leav immediately")
    assert result["score"] > 0.8
    close_words = [d for d in result["diffs"] if d["status"] == "close"]
    assert len(close_words) == 1
    assert close_words[0]["word"] == "leav"
    assert close_words[0]["expected"] == "leave"


def test_score_dictation_missing_word():
    result = score_dictation("Yes I have to leave immediately", "yes i have to leave")
    assert result["score"] < 1.0
    missing = [d for d in result["diffs"] if d["status"] == "missing"]
    assert len(missing) == 1
    assert missing[0]["word"] == "immediately"


def test_score_dictation_extra_word():
    result = score_dictation("Yes I have to leave", "yes i have to leave now")
    extra = [d for d in result["diffs"] if d["status"] == "extra"]
    assert len(extra) == 1
    assert extra[0]["word"] == "now"


def test_score_dictation_empty():
    result = score_dictation("Yes I have to leave", "")
    assert result["score"] == 0.0


def test_score_punctuation_ignored():
    result = score_dictation("Yes, I have to leave.", "yes i have to leave")
    assert result["score"] == 1.0


def test_xp_perfect():
    result = score_dictation("Hello world", "hello world")
    assert result["xp"] == 10


def test_xp_close():
    result = score_dictation("Hello world", "hello worl")
    assert result["xp"] == 5


def test_xp_bad():
    result = score_dictation("Hello world", "goodbye everyone")
    assert result["xp"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_scoring.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement scoring.py**

Create `app/services/scoring.py`:

```python
import re


def levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def _normalize(text: str) -> list[str]:
    text = re.sub(r"[^\w\s]", "", text.lower().strip())
    return text.split()


def score_dictation(expected: str, typed: str) -> dict:
    expected_words = _normalize(expected)
    typed_words = _normalize(typed)

    if not typed_words:
        diffs = [{"word": w, "status": "missing", "expected": None} for w in expected_words]
        return {"score": 0.0, "xp": 0, "diffs": diffs, "expected_text": expected}

    diffs = []
    e_idx = 0
    t_idx = 0

    while e_idx < len(expected_words) and t_idx < len(typed_words):
        ew = expected_words[e_idx]
        tw = typed_words[t_idx]

        if ew == tw:
            diffs.append({"word": tw, "status": "correct", "expected": None})
            e_idx += 1
            t_idx += 1
        elif levenshtein(ew, tw) <= 2:
            diffs.append({"word": tw, "status": "close", "expected": ew})
            e_idx += 1
            t_idx += 1
        else:
            if e_idx + 1 < len(expected_words) and expected_words[e_idx + 1] == tw:
                diffs.append({"word": ew, "status": "missing", "expected": None})
                e_idx += 1
            elif t_idx + 1 < len(typed_words) and typed_words[t_idx + 1] == ew:
                diffs.append({"word": tw, "status": "extra", "expected": None})
                t_idx += 1
            else:
                diffs.append({"word": tw, "status": "incorrect", "expected": ew})
                e_idx += 1
                t_idx += 1

    while e_idx < len(expected_words):
        diffs.append({"word": expected_words[e_idx], "status": "missing", "expected": None})
        e_idx += 1

    while t_idx < len(typed_words):
        diffs.append({"word": typed_words[t_idx], "status": "extra", "expected": None})
        t_idx += 1

    correct = sum(1 for d in diffs if d["status"] == "correct")
    close = sum(1 for d in diffs if d["status"] == "close")
    total_expected = len(expected_words)
    score = (correct + close * 0.8) / total_expected if total_expected > 0 else 0.0
    score = round(min(score, 1.0), 2)

    if score >= 0.95:
        xp = 10
    elif score >= 0.7:
        xp = 5
    else:
        xp = 0

    return {"score": score, "xp": xp, "diffs": diffs, "expected_text": expected}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_scoring.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add app/services/scoring.py tests/test_scoring.py
git commit -m "feat: add dictation scoring with Levenshtein fuzzy matching"
```

---

### Task 5: Spaced Repetition Service

**Files:**
- Create: `app/services/spaced_rep.py`
- Create: `tests/test_spaced_rep.py`

- [ ] **Step 1: Write spaced repetition tests**

Create `tests/test_spaced_rep.py`:

```python
from datetime import datetime, timedelta
from app.services.spaced_rep import next_review_date, update_bucket

BUCKET_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def test_next_review_bucket_1():
    now = datetime(2026, 4, 24, 12, 0)
    result = next_review_date(bucket=1, now=now)
    assert result == now + timedelta(days=1)


def test_next_review_bucket_5():
    now = datetime(2026, 4, 24, 12, 0)
    result = next_review_date(bucket=5, now=now)
    assert result == now + timedelta(days=30)


def test_update_bucket_correct_promotes():
    assert update_bucket(current_bucket=1, correct=True) == 2
    assert update_bucket(current_bucket=4, correct=True) == 5


def test_update_bucket_correct_max():
    assert update_bucket(current_bucket=5, correct=True) == 5


def test_update_bucket_incorrect_resets():
    assert update_bucket(current_bucket=3, correct=False) == 1
    assert update_bucket(current_bucket=5, correct=False) == 1


def test_update_bucket_incorrect_already_1():
    assert update_bucket(current_bucket=1, correct=False) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_spaced_rep.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement spaced_rep.py**

Create `app/services/spaced_rep.py`:

```python
from datetime import datetime, timedelta

BUCKET_INTERVALS = {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}


def next_review_date(bucket: int, now: datetime | None = None) -> datetime:
    if now is None:
        now = datetime.now()
    days = BUCKET_INTERVALS.get(bucket, 1)
    return now + timedelta(days=days)


def update_bucket(current_bucket: int, correct: bool) -> int:
    if correct:
        return min(current_bucket + 1, 5)
    return 1
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_spaced_rep.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add app/services/spaced_rep.py tests/test_spaced_rep.py
git commit -m "feat: add Leitner spaced repetition service"
```

---

### Task 6: Auth Router

**Files:**
- Create: `app/routers/auth.py`
- Add to: `tests/test_api.py`

- [ ] **Step 1: Write auth API tests**

Append to `tests/test_api.py`:

```python
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
from app.database import init_db


def _make_app():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db(db_path)
    app = create_app(db_path)
    return TestClient(app), db_path


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_api.py::test_register_and_login -v
```

Expected: FAIL — `cannot import name 'create_app' from 'app.main'`

- [ ] **Step 3: Implement auth router**

Create `app/routers/auth.py`:

```python
import hashlib
import secrets
import sqlite3
from fastapi import APIRouter, Request, Response, HTTPException
import bcrypt
from app.models import RegisterRequest, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSIONS: dict[str, int] = {}


def get_current_user_id(request: Request) -> int:
    session_id = request.cookies.get("session")
    if not session_id or session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return SESSIONS[session_id]


@router.post("/register")
def register(req: RegisterRequest, request: Request):
    db = request.app.state.db_path
    import sqlite3
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, ui_language) VALUES (?, ?, ?)",
            (req.username, pw_hash, req.ui_language),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Username already exists")
    user = conn.execute("SELECT id, username, ui_language FROM users WHERE username = ?", (req.username,)).fetchone()
    conn.close()
    return {"id": user["id"], "username": user["username"], "ui_language": user["ui_language"]}


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response):
    db = request.app.state.db_path
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
    conn.close()
    if not user or not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_id = secrets.token_hex(32)
    SESSIONS[session_id] = user["id"]
    response.set_cookie(key="session", value=session_id, httponly=True, samesite="lax")
    return {"message": "Logged in", "username": user["username"]}


@router.post("/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get("session")
    if session_id and session_id in SESSIONS:
        del SESSIONS[session_id]
    response.delete_cookie("session")
    return {"message": "Logged out"}
```

- [ ] **Step 4: Create app/main.py**

Create `app/main.py`:

```python
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import DB_PATH
from app.database import init_db
from app.routers import auth, lessons, practice, vocabulary


def create_app(db_path: Path | None = None) -> FastAPI:
    if db_path is None:
        db_path = DB_PATH
    init_db(db_path)

    app = FastAPI(title="English Learning App")
    app.state.db_path = db_path

    app.include_router(auth.router)
    app.include_router(lessons.router)
    app.include_router(practice.router)
    app.include_router(vocabulary.router)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
```

- [ ] **Step 5: Create stub routers for lessons, practice, vocabulary**

Create `app/routers/lessons.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/lessons", tags=["lessons"])
```

Create `app/routers/practice.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/practice", tags=["practice"])
```

Create `app/routers/vocabulary.py`:

```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])
```

- [ ] **Step 6: Run all tests**

```bash
python -m pytest tests/ -v
```

Expected: all passed

- [ ] **Step 7: Commit**

```bash
git add app/main.py app/routers/auth.py app/routers/lessons.py app/routers/practice.py app/routers/vocabulary.py tests/test_api.py
git commit -m "feat: add auth router with register/login/logout"
```

---

### Task 7: Lessons Router

**Files:**
- Modify: `app/routers/lessons.py`
- Add to: `tests/test_api.py`

- [ ] **Step 1: Write lessons API tests**

Append to `tests/test_api.py`:

```python
import json


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_api.py::test_list_lessons -v
```

Expected: FAIL — 404 or empty response

- [ ] **Step 3: Implement lessons router**

Replace `app/routers/lessons.py`:

```python
import json
import sqlite3
from fastapi import APIRouter, Request, HTTPException
from app.routers.auth import get_current_user_id

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("")
def list_lessons(request: Request):
    user_id = get_current_user_id(request)
    conn = sqlite3.connect(str(request.app.state.db_path))
    conn.row_factory = sqlite3.Row
    lessons = conn.execute("SELECT * FROM lessons ORDER BY id").fetchall()
    result = []
    for lesson in lessons:
        completed = conn.execute(
            "SELECT COUNT(DISTINCT sentence_id) FROM user_progress WHERE user_id = ? AND sentence_id LIKE ? AND score >= 0.7",
            (user_id, f"{lesson['id']}-%"),
        ).fetchone()[0]
        result.append({
            "id": lesson["id"],
            "title": lesson["title"],
            "title_zh": lesson["title_zh"],
            "title_vi": lesson["title_vi"],
            "difficulty": lesson["difficulty"],
            "category": lesson["category"],
            "sentence_count": lesson["sentence_count"],
            "completed_count": completed,
        })
    conn.close()
    return result


@router.get("/{lesson_id}")
def get_lesson(lesson_id: int, request: Request):
    get_current_user_id(request)
    conn = sqlite3.connect(str(request.app.state.db_path))
    conn.row_factory = sqlite3.Row
    lesson = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        raise HTTPException(status_code=404, detail="Lesson not found")
    sentences = conn.execute(
        "SELECT * FROM sentences WHERE lesson_id = ? ORDER BY idx", (lesson_id,)
    ).fetchall()
    conn.close()
    return {
        "id": lesson["id"],
        "title": lesson["title"],
        "title_zh": lesson["title_zh"],
        "title_vi": lesson["title_vi"],
        "difficulty": lesson["difficulty"],
        "category": lesson["category"],
        "sentence_count": lesson["sentence_count"],
        "sentences": [
            {
                "id": s["id"],
                "index": s["idx"],
                "text": s["text"],
                "translation_zh": s["translation_zh"],
                "translation_vi": s["translation_vi"],
                "words": json.loads(s["words_json"]),
                "constituents": json.loads(s["constituents_json"]),
            }
            for s in sentences
        ],
    }


@router.get("/{lesson_id}/sentences/{index}")
def get_sentence(lesson_id: int, index: int, request: Request):
    get_current_user_id(request)
    conn = sqlite3.connect(str(request.app.state.db_path))
    conn.row_factory = sqlite3.Row
    sentence = conn.execute(
        "SELECT * FROM sentences WHERE lesson_id = ? AND idx = ?", (lesson_id, index)
    ).fetchone()
    conn.close()
    if not sentence:
        raise HTTPException(status_code=404, detail="Sentence not found")
    return {
        "id": sentence["id"],
        "lesson_id": sentence["lesson_id"],
        "index": sentence["idx"],
        "text": sentence["text"],
        "translation_zh": sentence["translation_zh"],
        "translation_vi": sentence["translation_vi"],
        "words": json.loads(sentence["words_json"]),
        "constituents": json.loads(sentence["constituents_json"]),
    }
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add app/routers/lessons.py tests/test_api.py
git commit -m "feat: add lessons router with list/detail/sentence endpoints"
```

---

### Task 8: Practice Router (Dictation + Self-Rate + Stats + Review)

**Files:**
- Modify: `app/routers/practice.py`
- Add to: `tests/test_api.py`

- [ ] **Step 1: Write practice API tests**

Append to `tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_api.py::test_submit_dictation -v
```

Expected: FAIL

- [ ] **Step 3: Implement practice router**

Replace `app/routers/practice.py`:

```python
import json
import sqlite3
from datetime import datetime, date
from fastapi import APIRouter, Request, HTTPException
from app.models import DictationSubmit, SelfRateRequest
from app.routers.auth import get_current_user_id
from app.services.scoring import score_dictation
from app.services.spaced_rep import next_review_date, update_bucket

router = APIRouter(tags=["practice"])


def _get_conn(request: Request) -> sqlite3.Connection:
    conn = sqlite3.connect(str(request.app.state.db_path))
    conn.row_factory = sqlite3.Row
    return conn


@router.post("/api/practice/submit")
def submit_dictation(req: DictationSubmit, request: Request):
    user_id = get_current_user_id(request)
    conn = _get_conn(request)

    sentence = conn.execute("SELECT * FROM sentences WHERE id = ?", (req.sentence_id,)).fetchone()
    if not sentence:
        conn.close()
        raise HTTPException(status_code=404, detail="Sentence not found")

    result = score_dictation(sentence["text"], req.typed_text)
    now = datetime.now()
    correct = result["score"] >= 0.7

    progress = conn.execute(
        "SELECT * FROM user_progress WHERE user_id = ? AND sentence_id = ? AND mode = 'dictation'",
        (user_id, req.sentence_id),
    ).fetchone()

    if progress:
        new_bucket = update_bucket(progress["leitner_bucket"], correct)
        conn.execute(
            """UPDATE user_progress SET score = ?, attempts = attempts + 1,
               last_attempt = ?, next_review = ?, leitner_bucket = ?
               WHERE id = ?""",
            (result["score"], now.isoformat(), next_review_date(new_bucket, now).isoformat(), new_bucket, progress["id"]),
        )
    else:
        new_bucket = update_bucket(1, correct)
        conn.execute(
            """INSERT INTO user_progress (user_id, sentence_id, mode, score, attempts, last_attempt, next_review, leitner_bucket)
               VALUES (?, ?, 'dictation', ?, 1, ?, ?, ?)""",
            (user_id, req.sentence_id, result["score"], now.isoformat(), next_review_date(new_bucket, now).isoformat(), new_bucket),
        )

    conn.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (result["xp"], user_id))

    today = date.today().isoformat()
    user = conn.execute("SELECT last_practice_date, streak_days FROM users WHERE id = ?", (user_id,)).fetchone()
    if user["last_practice_date"] != today:
        yesterday = date.today().replace(day=date.today().day - 1).isoformat() if date.today().day > 1 else ""
        new_streak = (user["streak_days"] + 1) if user["last_practice_date"] == yesterday else 1
        conn.execute("UPDATE users SET last_practice_date = ?, streak_days = ? WHERE id = ?", (today, new_streak, user_id))

    words = json.loads(sentence["words_json"])
    for w in words:
        conn.execute(
            """INSERT INTO vocabulary (user_id, word, ipa, pos, seen_count, correct_count)
               VALUES (?, ?, ?, ?, 1, ?)
               ON CONFLICT(user_id, word) DO UPDATE SET seen_count = seen_count + 1, correct_count = correct_count + ?""",
            (user_id, w["word"].lower(), w["ipa"], w["pos"], 1 if correct else 0, 1 if correct else 0),
        )

    conn.commit()
    conn.close()

    return {"score": result["score"], "xp_earned": result["xp"], "diffs": result["diffs"], "expected_text": result["expected_text"]}


@router.post("/api/practice/self-rate")
def self_rate(req: SelfRateRequest, request: Request):
    user_id = get_current_user_id(request)
    conn = _get_conn(request)

    sentence = conn.execute("SELECT * FROM sentences WHERE id = ?", (req.sentence_id,)).fetchone()
    if not sentence:
        conn.close()
        raise HTTPException(status_code=404, detail="Sentence not found")

    correct = req.rating in ("good", "okay")
    score = {"good": 1.0, "okay": 0.7, "again": 0.3}[req.rating]
    now = datetime.now()

    progress = conn.execute(
        "SELECT * FROM user_progress WHERE user_id = ? AND sentence_id = ? AND mode = 'read_aloud'",
        (user_id, req.sentence_id),
    ).fetchone()

    if progress:
        new_bucket = update_bucket(progress["leitner_bucket"], correct)
        conn.execute(
            """UPDATE user_progress SET score = ?, attempts = attempts + 1,
               last_attempt = ?, next_review = ?, leitner_bucket = ?
               WHERE id = ?""",
            (score, now.isoformat(), next_review_date(new_bucket, now).isoformat(), new_bucket, progress["id"]),
        )
    else:
        new_bucket = update_bucket(1, correct)
        conn.execute(
            """INSERT INTO user_progress (user_id, sentence_id, mode, score, attempts, last_attempt, next_review, leitner_bucket)
               VALUES (?, ?, 'read_aloud', ?, 1, ?, ?, ?)""",
            (user_id, req.sentence_id, score, now.isoformat(), next_review_date(new_bucket, now).isoformat(), new_bucket),
        )

    conn.commit()
    conn.close()
    return {"message": "Rated", "rating": req.rating}


@router.get("/api/stats")
def get_stats(request: Request):
    user_id = get_current_user_id(request)
    conn = _get_conn(request)
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    total_practiced = conn.execute(
        "SELECT COUNT(DISTINCT sentence_id) FROM user_progress WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    total_words = conn.execute(
        "SELECT COUNT(*) FROM vocabulary WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    avg_score = conn.execute(
        "SELECT AVG(score) FROM user_progress WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    today = date.today().isoformat()
    sentences_today = conn.execute(
        "SELECT COUNT(DISTINCT sentence_id) FROM user_progress WHERE user_id = ? AND last_attempt LIKE ?",
        (user_id, f"{today}%"),
    ).fetchone()[0]
    conn.close()
    return {
        "xp": user["xp"],
        "streak_days": user["streak_days"],
        "total_sentences_practiced": total_practiced,
        "total_words_learned": total_words,
        "accuracy_percent": round((avg_score or 0) * 100, 1),
        "sentences_today": sentences_today,
        "daily_goal": user["daily_goal"],
    }


@router.get("/api/review/due")
def get_review_due(request: Request):
    user_id = get_current_user_id(request)
    conn = _get_conn(request)
    now = datetime.now().isoformat()
    rows = conn.execute(
        """SELECT p.sentence_id, p.mode, p.score, p.leitner_bucket, s.text, s.translation_zh, s.translation_vi
           FROM user_progress p JOIN sentences s ON p.sentence_id = s.id
           WHERE p.user_id = ? AND p.next_review <= ?
           ORDER BY p.next_review LIMIT 20""",
        (user_id, now),
    ).fetchall()
    conn.close()
    return [
        {
            "sentence_id": r["sentence_id"],
            "mode": r["mode"],
            "score": r["score"],
            "bucket": r["leitner_bucket"],
            "text": r["text"],
            "translation_zh": r["translation_zh"],
            "translation_vi": r["translation_vi"],
        }
        for r in rows
    ]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add app/routers/practice.py tests/test_api.py
git commit -m "feat: add practice router with dictation, self-rate, stats, review"
```

---

### Task 9: Vocabulary Router

**Files:**
- Modify: `app/routers/vocabulary.py`
- Add to: `tests/test_api.py`

- [ ] **Step 1: Write vocabulary API tests**

Append to `tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_api.py::test_vocabulary_after_practice -v
```

Expected: FAIL

- [ ] **Step 3: Implement vocabulary router**

Replace `app/routers/vocabulary.py`:

```python
import sqlite3
from fastapi import APIRouter, Request, Query
from app.routers.auth import get_current_user_id

router = APIRouter(prefix="/api/vocabulary", tags=["vocabulary"])


@router.get("")
def get_vocabulary(request: Request, filter: str = Query(default="all")):
    user_id = get_current_user_id(request)
    conn = sqlite3.connect(str(request.app.state.db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM vocabulary WHERE user_id = ? ORDER BY word", (user_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        ratio = r["correct_count"] / r["seen_count"] if r["seen_count"] > 0 else 0
        if ratio >= 0.8:
            status = "mastered"
        elif ratio >= 0.4:
            status = "learning"
        else:
            status = "weak"
        if filter != "all" and status != filter:
            continue
        result.append({
            "word": r["word"],
            "ipa": r["ipa"] or "",
            "pos": r["pos"] or "",
            "seen_count": r["seen_count"],
            "correct_count": r["correct_count"],
            "status": status,
        })
    return result


@router.get("/flashcards")
def get_flashcards(request: Request):
    user_id = get_current_user_id(request)
    conn = sqlite3.connect(str(request.app.state.db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT v.*, s.text, s.translation_zh, s.translation_vi
           FROM vocabulary v
           LEFT JOIN sentences s ON s.words_json LIKE '%' || v.word || '%'
           WHERE v.user_id = ?
           GROUP BY v.word
           ORDER BY v.correct_count * 1.0 / MAX(v.seen_count, 1) ASC
           LIMIT 20""",
        (user_id,),
    ).fetchall()
    conn.close()
    return [
        {
            "word": r["word"],
            "ipa": r["ipa"] or "",
            "pos": r["pos"] or "",
            "example_sentence": r["text"] or "",
            "translation_zh": r["translation_zh"] or "",
            "translation_vi": r["translation_vi"] or "",
        }
        for r in rows
    ]
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add app/routers/vocabulary.py tests/test_api.py
git commit -m "feat: add vocabulary router with word bank and flashcards"
```

---

### Task 10: User Settings Endpoint

**Files:**
- Modify: `app/routers/auth.py`
- Add to: `tests/test_api.py`

- [ ] **Step 1: Write settings tests**

Append to `tests/test_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_api.py::test_get_profile -v
```

Expected: FAIL — 404

- [ ] **Step 3: Add profile and settings endpoints to auth router**

Append to `app/routers/auth.py`:

```python
from app.models import SettingsUpdate


@router.get("/api/user/profile")
def get_profile(request: Request):
    user_id = get_current_user_id(request)
    conn = sqlite3.connect(str(request.app.state.db_path))
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    today = __import__("datetime").date.today().isoformat()
    sentences_today = conn.execute(
        "SELECT COUNT(DISTINCT sentence_id) FROM user_progress WHERE user_id = ? AND last_attempt LIKE ?",
        (user_id, f"{today}%"),
    ).fetchone()[0]
    conn.close()
    return {
        "username": user["username"],
        "ui_language": user["ui_language"],
        "daily_goal": user["daily_goal"],
        "tts_speed": user["tts_speed"],
        "xp": user["xp"],
        "streak_days": user["streak_days"],
        "sentences_today": sentences_today,
    }


@router.put("/api/user/settings")
def update_settings(req: SettingsUpdate, request: Request):
    user_id = get_current_user_id(request)
    conn = sqlite3.connect(str(request.app.state.db_path))
    updates = []
    params = []
    if req.ui_language is not None:
        updates.append("ui_language = ?")
        params.append(req.ui_language)
    if req.daily_goal is not None:
        updates.append("daily_goal = ?")
        params.append(req.daily_goal)
    if req.tts_speed is not None:
        updates.append("tts_speed = ?")
        params.append(req.tts_speed)
    if updates:
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    conn.close()
    return {"message": "Settings updated"}
```

Note: the profile/settings endpoints use `/api/user/` prefix but are registered on the auth router which has `/api/auth` prefix. Because these paths are absolute (start with `/api/user`), use `@router.get("/api/user/profile")` — but FastAPI will prepend the router prefix. Instead, register these on the app directly. Better approach: add them with the full path using `@router.api_route`. Simplest fix: remove the prefix from the decorator and include the full path.

Actually, the cleanest approach: these endpoints use full paths starting with `/api/user/` so they need to bypass the `/api/auth` prefix. Add them to `app/main.py` directly, or create a separate user router. Let's add them directly to `auth.py` but without the router prefix by using the app-level include. The simplest working approach is to use the `path` directly since FastAPI router prefix is `/api/auth`:

Change the approach — add these two endpoints as separate functions registered on `app/main.py`:

Actually, the simplest fix: put `/user/profile` and `/user/settings` on the auth router and they become `/api/auth/user/profile`. OR create a small user router. Let me use a clean approach:

Add to `app/main.py` after including routers:

```python
from app.routers.auth import get_current_user_id, get_profile, update_settings

app.get("/api/user/profile")(get_profile)
app.put("/api/user/settings")(update_settings)
```

This is getting complicated. Cleaner approach — just adjust the test URLs to match the router prefix, or add the functions directly in main. Let me use the direct approach in main.py:

Replace the endpoints — add them to `app/main.py`'s `create_app` function:

```python
def create_app(db_path: Path | None = None) -> FastAPI:
    # ... existing code ...

    @app.get("/api/user/profile")
    def profile(request: Request):
        from app.routers.auth import get_current_user_id
        user_id = get_current_user_id(request)
        conn = sqlite3.connect(str(request.app.state.db_path))
        conn.row_factory = sqlite3.Row
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        today = date.today().isoformat()
        sentences_today = conn.execute(
            "SELECT COUNT(DISTINCT sentence_id) FROM user_progress WHERE user_id = ? AND last_attempt LIKE ?",
            (user_id, f"{today}%"),
        ).fetchone()[0]
        conn.close()
        return {
            "username": user["username"],
            "ui_language": user["ui_language"],
            "daily_goal": user["daily_goal"],
            "tts_speed": user["tts_speed"],
            "xp": user["xp"],
            "streak_days": user["streak_days"],
            "sentences_today": sentences_today,
        }

    @app.put("/api/user/settings")
    def settings(req: SettingsUpdate, request: Request):
        from app.routers.auth import get_current_user_id
        user_id = get_current_user_id(request)
        conn = sqlite3.connect(str(request.app.state.db_path))
        updates, params = [], []
        if req.ui_language is not None:
            updates.append("ui_language = ?")
            params.append(req.ui_language)
        if req.daily_goal is not None:
            updates.append("daily_goal = ?")
            params.append(req.daily_goal)
        if req.tts_speed is not None:
            updates.append("tts_speed = ?")
            params.append(req.tts_speed)
        if updates:
            params.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
        conn.close()
        return {"message": "Settings updated"}

    return app
```

Add these imports to `app/main.py`:

```python
import sqlite3
from datetime import date
from fastapi import Request
from app.models import SettingsUpdate
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add app/main.py app/routers/auth.py tests/test_api.py
git commit -m "feat: add user profile and settings endpoints"
```

---

### Task 11: Seed Lesson Data

**Files:**
- Create: `data/lessons/lesson_001.json`
- Create: `data/lessons/lesson_002.json`
- Create: `data/lessons/lesson_003.json`
- Create: `tools/import_lessons.py`

- [ ] **Step 1: Create lesson_001.json (Greetings - A1)**

Create `data/lessons/lesson_001.json`:

```json
{
  "id": 1,
  "title": "Greetings",
  "title_zh": "问候",
  "title_vi": "Chao hoi",
  "difficulty": "A1",
  "category": "daily_conversation",
  "sentences": [
    {
      "index": 1,
      "text": "Hello, how are you?",
      "translation_zh": "你好，你怎么样？",
      "translation_vi": "Xin chao, ban co khoe khong?",
      "words": [
        {"word": "Hello", "ipa": "/həˈloʊ/", "pos": "interjection", "pos_zh": "感叹词", "pos_vi": "than tu", "role": "greeting", "role_zh": "问候语", "role_vi": "loi chao", "group": 0, "group_color": "#795548"},
        {"word": "how", "ipa": "/haʊ/", "pos": "adverb", "pos_zh": "副词", "pos_vi": "trang tu", "role": "adverbial", "role_zh": "状语", "role_vi": "trang ngu", "group": 1, "group_color": "#4CAF50"},
        {"word": "are", "ipa": "/ɑːr/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "you", "ipa": "/juː/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 1, "group_color": "#9C27B0"}
      ],
      "constituents": [
        {"group": 0, "label_en": "greeting", "label_zh": "问候语", "label_vi": "loi chao", "word_indices": [0], "color": "#795548"},
        {"group": 1, "label_en": "question", "label_zh": "疑问句", "label_vi": "cau hoi", "word_indices": [1, 2, 3], "color": "#4CAF50"}
      ]
    },
    {
      "index": 2,
      "text": "I am fine, thank you.",
      "translation_zh": "我很好，谢谢你。",
      "translation_vi": "Toi khoe, cam on ban.",
      "words": [
        {"word": "I", "ipa": "/aɪ/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "am", "ipa": "/æm/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 0, "group_color": "#F44336"},
        {"word": "fine", "ipa": "/faɪn/", "pos": "adjective", "pos_zh": "形容词", "pos_vi": "tinh tu", "role": "complement", "role_zh": "表语", "role_vi": "bo ngu", "group": 0, "group_color": "#FF9800"},
        {"word": "thank", "ipa": "/θæŋk/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "you", "ipa": "/juː/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#9C27B0"}
      ],
      "constituents": [
        {"group": 0, "label_en": "main clause", "label_zh": "主句", "label_vi": "menh de chinh", "word_indices": [0, 1, 2], "color": "#2196F3"},
        {"group": 1, "label_en": "thanks", "label_zh": "感谢", "label_vi": "cam on", "word_indices": [3, 4], "color": "#4CAF50"}
      ]
    },
    {
      "index": 3,
      "text": "Nice to meet you.",
      "translation_zh": "很高兴认识你。",
      "translation_vi": "Rat vui duoc gap ban.",
      "words": [
        {"word": "Nice", "ipa": "/naɪs/", "pos": "adjective", "pos_zh": "形容词", "pos_vi": "tinh tu", "role": "complement", "role_zh": "表语", "role_vi": "bo ngu", "group": 0, "group_color": "#FF9800"},
        {"word": "to", "ipa": "/tuː/", "pos": "particle", "pos_zh": "小品词", "pos_vi": "tieu tu", "role": "infinitive", "role_zh": "不定式", "role_vi": "dong tu nguyen mau", "group": 1, "group_color": "#00BCD4"},
        {"word": "meet", "ipa": "/miːt/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "you", "ipa": "/juː/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#9C27B0"}
      ],
      "constituents": [
        {"group": 0, "label_en": "adjective", "label_zh": "形容词", "label_vi": "tinh tu", "word_indices": [0], "color": "#FF9800"},
        {"group": 1, "label_en": "infinitive phrase", "label_zh": "不定式短语", "label_vi": "cum dong tu nguyen mau", "word_indices": [1, 2, 3], "color": "#4CAF50"}
      ]
    },
    {
      "index": 4,
      "text": "What is your name?",
      "translation_zh": "你叫什么名字？",
      "translation_vi": "Ban ten la gi?",
      "words": [
        {"word": "What", "ipa": "/wɑːt/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "is", "ipa": "/ɪz/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 0, "group_color": "#F44336"},
        {"word": "your", "ipa": "/jʊr/", "pos": "determiner", "pos_zh": "限定词", "pos_vi": "han dinh tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 1, "group_color": "#3F51B5"},
        {"word": "name", "ipa": "/neɪm/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 1, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "question word + verb", "label_zh": "疑问词+动词", "label_vi": "tu hoi + dong tu", "word_indices": [0, 1], "color": "#9C27B0"},
        {"group": 1, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [2, 3], "color": "#2196F3"}
      ]
    },
    {
      "index": 5,
      "text": "My name is David.",
      "translation_zh": "我的名字是大卫。",
      "translation_vi": "Ten toi la David.",
      "words": [
        {"word": "My", "ipa": "/maɪ/", "pos": "determiner", "pos_zh": "限定词", "pos_vi": "han dinh tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 0, "group_color": "#3F51B5"},
        {"word": "name", "ipa": "/neɪm/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#2196F3"},
        {"word": "is", "ipa": "/ɪz/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "David", "ipa": "/ˈdeɪvɪd/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "complement", "role_zh": "表语", "role_vi": "bo ngu", "group": 1, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0, 1], "color": "#2196F3"},
        {"group": 1, "label_en": "predicate", "label_zh": "谓语", "label_vi": "vi ngu", "word_indices": [2, 3], "color": "#F44336"}
      ]
    },
    {
      "index": 6,
      "text": "Good morning!",
      "translation_zh": "早上好！",
      "translation_vi": "Chao buoi sang!",
      "words": [
        {"word": "Good", "ipa": "/ɡʊd/", "pos": "adjective", "pos_zh": "形容词", "pos_vi": "tinh tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 0, "group_color": "#FF9800"},
        {"word": "morning", "ipa": "/ˈmɔːrnɪŋ/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 0, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "greeting phrase", "label_zh": "问候短语", "label_vi": "cum chao hoi", "word_indices": [0, 1], "color": "#795548"}
      ]
    }
  ]
}
```

- [ ] **Step 2: Create lesson_002.json (Daily Routines - A1)**

Create `data/lessons/lesson_002.json`:

```json
{
  "id": 2,
  "title": "Daily Routines",
  "title_zh": "日常生活",
  "title_vi": "Sinh hoat hang ngay",
  "difficulty": "A1",
  "category": "daily_conversation",
  "sentences": [
    {
      "index": 1,
      "text": "I wake up at seven o'clock.",
      "translation_zh": "我七点钟起床。",
      "translation_vi": "Toi thuc day luc bay gio.",
      "words": [
        {"word": "I", "ipa": "/aɪ/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "wake", "ipa": "/weɪk/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "up", "ipa": "/ʌp/", "pos": "particle", "pos_zh": "小品词", "pos_vi": "tieu tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#00BCD4"},
        {"word": "at", "ipa": "/æt/", "pos": "preposition", "pos_zh": "介词", "pos_vi": "gioi tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#607D8B"},
        {"word": "seven", "ipa": "/ˈsɛvən/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#2196F3"},
        {"word": "o'clock", "ipa": "/əˈklɑːk/", "pos": "adverb", "pos_zh": "副词", "pos_vi": "trang tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#4CAF50"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate", "label_zh": "谓语", "label_vi": "vi ngu", "word_indices": [1, 2], "color": "#F44336"},
        {"group": 2, "label_en": "time adverbial", "label_zh": "时间状语", "label_vi": "trang ngu thoi gian", "word_indices": [3, 4, 5], "color": "#FF9800"}
      ]
    },
    {
      "index": 2,
      "text": "She goes to school every day.",
      "translation_zh": "她每天去学校。",
      "translation_vi": "Co ay di hoc moi ngay.",
      "words": [
        {"word": "She", "ipa": "/ʃiː/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "goes", "ipa": "/ɡoʊz/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "to", "ipa": "/tuː/", "pos": "preposition", "pos_zh": "介词", "pos_vi": "gioi tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#607D8B"},
        {"word": "school", "ipa": "/skuːl/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#2196F3"},
        {"word": "every", "ipa": "/ˈɛvri/", "pos": "determiner", "pos_zh": "限定词", "pos_vi": "han dinh tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#3F51B5"},
        {"word": "day", "ipa": "/deɪ/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate", "label_zh": "谓语", "label_vi": "vi ngu", "word_indices": [1, 2, 3], "color": "#F44336"},
        {"group": 2, "label_en": "time adverbial", "label_zh": "时间状语", "label_vi": "trang ngu thoi gian", "word_indices": [4, 5], "color": "#FF9800"}
      ]
    },
    {
      "index": 3,
      "text": "We have breakfast at eight.",
      "translation_zh": "我们八点吃早餐。",
      "translation_vi": "Chung toi an sang luc tam gio.",
      "words": [
        {"word": "We", "ipa": "/wiː/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "have", "ipa": "/hæv/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "breakfast", "ipa": "/ˈbrɛkfəst/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#2196F3"},
        {"word": "at", "ipa": "/æt/", "pos": "preposition", "pos_zh": "介词", "pos_vi": "gioi tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#607D8B"},
        {"word": "eight", "ipa": "/eɪt/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate + object", "label_zh": "谓语+宾语", "label_vi": "vi ngu + tan ngu", "word_indices": [1, 2], "color": "#F44336"},
        {"group": 2, "label_en": "time adverbial", "label_zh": "时间状语", "label_vi": "trang ngu thoi gian", "word_indices": [3, 4], "color": "#FF9800"}
      ]
    },
    {
      "index": 4,
      "text": "He reads books before bed.",
      "translation_zh": "他睡前看书。",
      "translation_vi": "Anh ay doc sach truoc khi ngu.",
      "words": [
        {"word": "He", "ipa": "/hiː/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "reads", "ipa": "/riːdz/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "books", "ipa": "/bʊks/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#2196F3"},
        {"word": "before", "ipa": "/bɪˈfɔːr/", "pos": "preposition", "pos_zh": "介词", "pos_vi": "gioi tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#607D8B"},
        {"word": "bed", "ipa": "/bɛd/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "time_adverbial", "role_zh": "时间状语", "role_vi": "trang ngu thoi gian", "group": 2, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate + object", "label_zh": "谓语+宾语", "label_vi": "vi ngu + tan ngu", "word_indices": [1, 2], "color": "#F44336"},
        {"group": 2, "label_en": "time adverbial", "label_zh": "时间状语", "label_vi": "trang ngu thoi gian", "word_indices": [3, 4], "color": "#FF9800"}
      ]
    },
    {
      "index": 5,
      "text": "They eat lunch together.",
      "translation_zh": "他们一起吃午饭。",
      "translation_vi": "Ho an trua cung nhau.",
      "words": [
        {"word": "They", "ipa": "/ðeɪ/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "eat", "ipa": "/iːt/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "lunch", "ipa": "/lʌntʃ/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#2196F3"},
        {"word": "together", "ipa": "/təˈɡɛðər/", "pos": "adverb", "pos_zh": "副词", "pos_vi": "trang tu", "role": "manner_adverbial", "role_zh": "方式状语", "role_vi": "trang ngu cach thuc", "group": 2, "group_color": "#4CAF50"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate + object", "label_zh": "谓语+宾语", "label_vi": "vi ngu + tan ngu", "word_indices": [1, 2], "color": "#F44336"},
        {"group": 2, "label_en": "manner adverbial", "label_zh": "方式状语", "label_vi": "trang ngu cach thuc", "word_indices": [3], "color": "#4CAF50"}
      ]
    }
  ]
}
```

- [ ] **Step 3: Create lesson_003.json (At the Restaurant - A1)**

Create `data/lessons/lesson_003.json`:

```json
{
  "id": 3,
  "title": "At the Restaurant",
  "title_zh": "在餐厅",
  "title_vi": "Tai nha hang",
  "difficulty": "A1",
  "category": "travel",
  "sentences": [
    {
      "index": 1,
      "text": "Can I see the menu please?",
      "translation_zh": "请问我可以看一下菜单吗？",
      "translation_vi": "Cho toi xem thuc don duoc khong?",
      "words": [
        {"word": "Can", "ipa": "/kæn/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "auxiliary", "role_zh": "助动词", "role_vi": "tro dong tu", "group": 0, "group_color": "#F44336"},
        {"word": "I", "ipa": "/aɪ/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "see", "ipa": "/siː/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "the", "ipa": "/ðə/", "pos": "determiner", "pos_zh": "限定词", "pos_vi": "han dinh tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 1, "group_color": "#3F51B5"},
        {"word": "menu", "ipa": "/ˈmɛnjuː/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#2196F3"},
        {"word": "please", "ipa": "/pliːz/", "pos": "adverb", "pos_zh": "副词", "pos_vi": "trang tu", "role": "politeness", "role_zh": "礼貌用语", "role_vi": "tu lich su", "group": 2, "group_color": "#4CAF50"}
      ],
      "constituents": [
        {"group": 0, "label_en": "modal + subject", "label_zh": "情态动词+主语", "label_vi": "dong tu tinh thai + chu ngu", "word_indices": [0, 1], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate + object", "label_zh": "谓语+宾语", "label_vi": "vi ngu + tan ngu", "word_indices": [2, 3, 4], "color": "#F44336"},
        {"group": 2, "label_en": "politeness marker", "label_zh": "礼貌用语", "label_vi": "tu lich su", "word_indices": [5], "color": "#4CAF50"}
      ]
    },
    {
      "index": 2,
      "text": "I would like a glass of water.",
      "translation_zh": "我想要一杯水。",
      "translation_vi": "Toi muon mot ly nuoc.",
      "words": [
        {"word": "I", "ipa": "/aɪ/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "would", "ipa": "/wʊd/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "auxiliary", "role_zh": "助动词", "role_vi": "tro dong tu", "group": 1, "group_color": "#F44336"},
        {"word": "like", "ipa": "/laɪk/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "a", "ipa": "/ə/", "pos": "determiner", "pos_zh": "限定词", "pos_vi": "han dinh tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 2, "group_color": "#3F51B5"},
        {"word": "glass", "ipa": "/ɡlæs/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 2, "group_color": "#2196F3"},
        {"word": "of", "ipa": "/ʌv/", "pos": "preposition", "pos_zh": "介词", "pos_vi": "gioi tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 2, "group_color": "#607D8B"},
        {"word": "water", "ipa": "/ˈwɔːtər/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 2, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate", "label_zh": "谓语", "label_vi": "vi ngu", "word_indices": [1, 2], "color": "#F44336"},
        {"group": 2, "label_en": "object", "label_zh": "宾语", "label_vi": "tan ngu", "word_indices": [3, 4, 5, 6], "color": "#2196F3"}
      ]
    },
    {
      "index": 3,
      "text": "The food is delicious.",
      "translation_zh": "这食物很好吃。",
      "translation_vi": "Mon an rat ngon.",
      "words": [
        {"word": "The", "ipa": "/ðə/", "pos": "determiner", "pos_zh": "限定词", "pos_vi": "han dinh tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 0, "group_color": "#3F51B5"},
        {"word": "food", "ipa": "/fuːd/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#2196F3"},
        {"word": "is", "ipa": "/ɪz/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "delicious", "ipa": "/dɪˈlɪʃəs/", "pos": "adjective", "pos_zh": "形容词", "pos_vi": "tinh tu", "role": "complement", "role_zh": "表语", "role_vi": "bo ngu", "group": 1, "group_color": "#FF9800"}
      ],
      "constituents": [
        {"group": 0, "label_en": "subject", "label_zh": "主语", "label_vi": "chu ngu", "word_indices": [0, 1], "color": "#2196F3"},
        {"group": 1, "label_en": "predicate + complement", "label_zh": "谓语+表语", "label_vi": "vi ngu + bo ngu", "word_indices": [2, 3], "color": "#F44336"}
      ]
    },
    {
      "index": 4,
      "text": "How much does it cost?",
      "translation_zh": "这要多少钱？",
      "translation_vi": "Cai nay gia bao nhieu?",
      "words": [
        {"word": "How", "ipa": "/haʊ/", "pos": "adverb", "pos_zh": "副词", "pos_vi": "trang tu", "role": "adverbial", "role_zh": "状语", "role_vi": "trang ngu", "group": 0, "group_color": "#4CAF50"},
        {"word": "much", "ipa": "/mʌtʃ/", "pos": "adverb", "pos_zh": "副词", "pos_vi": "trang tu", "role": "adverbial", "role_zh": "状语", "role_vi": "trang ngu", "group": 0, "group_color": "#4CAF50"},
        {"word": "does", "ipa": "/dʌz/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "auxiliary", "role_zh": "助动词", "role_vi": "tro dong tu", "group": 1, "group_color": "#F44336"},
        {"word": "it", "ipa": "/ɪt/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 1, "group_color": "#9C27B0"},
        {"word": "cost", "ipa": "/kɔːst/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"}
      ],
      "constituents": [
        {"group": 0, "label_en": "question phrase", "label_zh": "疑问短语", "label_vi": "cum tu hoi", "word_indices": [0, 1], "color": "#4CAF50"},
        {"group": 1, "label_en": "auxiliary + subject + verb", "label_zh": "助动词+主语+动词", "label_vi": "tro dong tu + chu ngu + dong tu", "word_indices": [2, 3, 4], "color": "#F44336"}
      ]
    },
    {
      "index": 5,
      "text": "Could I have the bill?",
      "translation_zh": "请给我账单好吗？",
      "translation_vi": "Cho toi xin hoa don?",
      "words": [
        {"word": "Could", "ipa": "/kʊd/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "auxiliary", "role_zh": "助动词", "role_vi": "tro dong tu", "group": 0, "group_color": "#F44336"},
        {"word": "I", "ipa": "/aɪ/", "pos": "pronoun", "pos_zh": "代词", "pos_vi": "dai tu", "role": "subject", "role_zh": "主语", "role_vi": "chu ngu", "group": 0, "group_color": "#9C27B0"},
        {"word": "have", "ipa": "/hæv/", "pos": "verb", "pos_zh": "动词", "pos_vi": "dong tu", "role": "predicate", "role_zh": "谓语", "role_vi": "vi ngu", "group": 1, "group_color": "#F44336"},
        {"word": "the", "ipa": "/ðə/", "pos": "determiner", "pos_zh": "限定词", "pos_vi": "han dinh tu", "role": "attributive", "role_zh": "定语", "role_vi": "dinh ngu", "group": 1, "group_color": "#3F51B5"},
        {"word": "bill", "ipa": "/bɪl/", "pos": "noun", "pos_zh": "名词", "pos_vi": "danh tu", "role": "object", "role_zh": "宾语", "role_vi": "tan ngu", "group": 1, "group_color": "#2196F3"}
      ],
      "constituents": [
        {"group": 0, "label_en": "modal + subject", "label_zh": "情态动词+主语", "label_vi": "dong tu tinh thai + chu ngu", "word_indices": [0, 1], "color": "#9C27B0"},
        {"group": 1, "label_en": "predicate + object", "label_zh": "谓语+宾语", "label_vi": "vi ngu + tan ngu", "word_indices": [2, 3, 4], "color": "#F44336"}
      ]
    }
  ]
}
```

- [ ] **Step 4: Create import_lessons.py**

Create `tools/import_lessons.py`:

```python
import json
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "english_learning.db"
LESSONS_DIR = BASE_DIR / "data" / "lessons"


def import_lesson(conn: sqlite3.Connection, filepath: Path):
    with open(filepath) as f:
        data = json.load(f)

    conn.execute(
        "INSERT OR REPLACE INTO lessons (id, title, title_zh, title_vi, difficulty, category, sentence_count) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["id"], data["title"], data["title_zh"], data["title_vi"], data["difficulty"], data["category"], len(data["sentences"])),
    )

    for s in data["sentences"]:
        sid = f"{data['id']}-{s['index']:02d}"
        conn.execute(
            "INSERT OR REPLACE INTO sentences (id, lesson_id, idx, text, translation_zh, translation_vi, words_json, constituents_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, data["id"], s["index"], s["text"], s["translation_zh"], s["translation_vi"], json.dumps(s["words"]), json.dumps(s["constituents"])),
        )

    conn.commit()
    print(f"Imported: {data['title']} ({len(data['sentences'])} sentences)")


def main():
    from app.database import init_db
    init_db(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))

    files = sorted(LESSONS_DIR.glob("lesson_*.json"))
    if not files:
        print("No lesson files found in", LESSONS_DIR)
        sys.exit(1)

    for f in files:
        import_lesson(conn, f)

    total = conn.execute("SELECT COUNT(*) FROM sentences").fetchone()[0]
    print(f"\nDone. Total sentences in DB: {total}")
    conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the import**

```bash
cd /fsx-neo/dedicated-fsx-data-repo-neo-us-east-1/toyng/toyng_ws/projects/Personalized_Product_search/englisht_turorial
python -m tools.import_lessons
```

Expected output:
```
Imported: Greetings (6 sentences)
Imported: Daily Routines (5 sentences)
Imported: At the Restaurant (5 sentences)

Done. Total sentences in DB: 16
```

- [ ] **Step 6: Commit**

```bash
git add data/lessons/ tools/import_lessons.py
git commit -m "feat: add 3 starter lessons and import script"
```

---

### Task 12: Frontend - SPA Shell and Router

**Files:**
- Create: `app/static/index.html`
- Create: `app/static/js/app.js`
- Create: `app/static/js/i18n.js`

- [ ] **Step 1: Create index.html**

Create `app/static/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>English Learning</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <div id="app">
        <div id="page-login" class="page active">
            <div class="login-container">
                <h1 class="login-title">
                    <span class="title-en">English Learning</span>
                    <span class="title-zh">英语学习</span>
                    <span class="title-vi">Hoc tieng Anh</span>
                </h1>
                <p class="login-subtitle" data-i18n="login_subtitle">Master English with rich sentence analysis</p>
                <div class="lang-selector">
                    <button class="lang-btn active" data-lang="zh">中文</button>
                    <button class="lang-btn" data-lang="vi">Tieng Viet</button>
                </div>
                <div class="tab-bar">
                    <button class="tab-btn active" data-tab="login" data-i18n="login">Login</button>
                    <button class="tab-btn" data-tab="register" data-i18n="register">Register</button>
                </div>
                <form id="login-form" class="auth-form">
                    <input type="text" id="login-username" placeholder="Username" required>
                    <input type="password" id="login-password" placeholder="Password" required>
                    <button type="submit" class="btn-primary" data-i18n="login">Login</button>
                    <p id="login-error" class="error-msg"></p>
                </form>
                <form id="register-form" class="auth-form" style="display:none">
                    <input type="text" id="reg-username" placeholder="Username" required>
                    <input type="password" id="reg-password" placeholder="Password" required>
                    <button type="submit" class="btn-primary" data-i18n="register">Register</button>
                    <p id="reg-error" class="error-msg"></p>
                </form>
            </div>
        </div>

        <div id="page-dashboard" class="page">
            <header class="top-bar">
                <div class="user-info">
                    <span id="dash-username" class="username"></span>
                </div>
                <div class="stats-bar">
                    <span class="stat-item" title="Streak"><span class="flame">&#128293;</span> <span id="dash-streak">0</span></span>
                    <span class="stat-item" title="XP">XP: <span id="dash-xp">0</span></span>
                    <span class="stat-item" title="Today"><span id="dash-today">0</span>/<span id="dash-goal">5</span></span>
                </div>
                <div class="top-actions">
                    <button id="btn-vocab" class="icon-btn" data-i18n-title="vocabulary">&#128218;</button>
                    <button id="btn-settings" class="icon-btn" data-i18n-title="settings">&#9881;</button>
                    <button id="btn-logout" class="icon-btn" title="Logout">&#10005;</button>
                </div>
            </header>
            <div class="dashboard-content">
                <div class="progress-card">
                    <div class="progress-ring-container">
                        <svg class="progress-ring" width="100" height="100">
                            <circle class="progress-ring-bg" cx="50" cy="50" r="42" />
                            <circle id="progress-ring-fill" class="progress-ring-fill" cx="50" cy="50" r="42" />
                        </svg>
                        <span id="progress-pct" class="progress-pct">0%</span>
                    </div>
                    <div class="progress-text">
                        <span data-i18n="todays_progress">Today's Progress</span>
                    </div>
                </div>
                <button id="btn-review" class="btn-review" data-i18n="quick_review">Quick Review</button>
                <div class="filter-bar">
                    <select id="filter-difficulty">
                        <option value="all" data-i18n="all_levels">All Levels</option>
                        <option value="A1">A1</option>
                        <option value="A2">A2</option>
                        <option value="B1">B1</option>
                        <option value="B2">B2</option>
                    </select>
                </div>
                <div id="lesson-grid" class="lesson-grid"></div>
            </div>
        </div>

        <div id="page-lesson" class="page">
            <header class="lesson-header">
                <button id="btn-back" class="icon-btn">&#8592;</button>
                <span id="lesson-title" class="lesson-title-text"></span>
                <span id="sentence-counter" class="sentence-counter"></span>
            </header>
            <div id="annotation-area" class="annotation-area"></div>
            <div class="audio-controls">
                <button id="btn-play" class="icon-btn play-btn">&#9654;</button>
                <button id="btn-repeat" class="icon-btn" data-i18n-title="repeat">&#128260;</button>
                <div class="speed-control">
                    <label data-i18n="speed">Speed</label>
                    <input type="range" id="speed-slider" min="0.5" max="2.0" step="0.1" value="1.0">
                    <span id="speed-value">1.0x</span>
                </div>
            </div>
            <div class="mode-tabs">
                <button class="mode-tab active" data-mode="learn" data-i18n="learn">Learn</button>
                <button class="mode-tab" data-mode="read_aloud" data-i18n="read_aloud">Read Aloud</button>
                <button class="mode-tab" data-mode="dictation" data-i18n="dictation">Dictation</button>
            </div>
            <div id="mode-content" class="mode-content">
                <div id="mode-learn" class="mode-panel active">
                    <p class="mode-hint" data-i18n="learn_hint">Study the sentence structure and listen to the pronunciation.</p>
                </div>
                <div id="mode-read-aloud" class="mode-panel">
                    <p class="mode-hint" data-i18n="read_aloud_hint">Listen and repeat. Rate your pronunciation.</p>
                    <div class="rate-buttons">
                        <button class="rate-btn rate-good" data-rating="good" data-i18n="good">Good</button>
                        <button class="rate-btn rate-okay" data-rating="okay" data-i18n="okay">Okay</button>
                        <button class="rate-btn rate-again" data-rating="again" data-i18n="again">Again</button>
                    </div>
                </div>
                <div id="mode-dictation" class="mode-panel">
                    <p class="mode-hint" data-i18n="dictation_hint">Type what you hear:</p>
                    <textarea id="dictation-input" class="dictation-input" rows="2" placeholder="Type here..."></textarea>
                    <button id="btn-submit-dictation" class="btn-primary" data-i18n="submit">Submit</button>
                    <div id="dictation-result" class="dictation-result" style="display:none"></div>
                </div>
            </div>
            <div class="sentence-nav">
                <button id="btn-prev" class="nav-btn">&#8592;</button>
                <span id="nav-counter" class="nav-counter"></span>
                <button id="btn-next" class="nav-btn">&#8594;</button>
            </div>
        </div>

        <div id="page-vocabulary" class="page">
            <header class="top-bar">
                <button id="vocab-back" class="icon-btn">&#8592;</button>
                <h2 data-i18n="vocabulary">Vocabulary</h2>
                <div class="vocab-filter">
                    <select id="vocab-filter-select">
                        <option value="all" data-i18n="all">All</option>
                        <option value="mastered" data-i18n="mastered">Mastered</option>
                        <option value="learning" data-i18n="learning">Learning</option>
                        <option value="weak" data-i18n="weak">Weak</option>
                    </select>
                </div>
            </header>
            <div id="vocab-list" class="vocab-list"></div>
            <button id="btn-flashcards" class="btn-primary" data-i18n="flashcard_mode">Flashcard Mode</button>
            <div id="flashcard-area" class="flashcard-area" style="display:none"></div>
        </div>

        <div id="page-settings" class="page">
            <header class="top-bar">
                <button id="settings-back" class="icon-btn">&#8592;</button>
                <h2 data-i18n="settings">Settings</h2>
            </header>
            <div class="settings-form">
                <div class="setting-item">
                    <label data-i18n="ui_language">UI Language</label>
                    <select id="setting-language">
                        <option value="zh">中文</option>
                        <option value="vi">Tieng Viet</option>
                    </select>
                </div>
                <div class="setting-item">
                    <label data-i18n="tts_speed">TTS Speed</label>
                    <input type="range" id="setting-tts-speed" min="0.5" max="2.0" step="0.1" value="1.0">
                    <span id="setting-speed-val">1.0x</span>
                </div>
                <div class="setting-item">
                    <label data-i18n="daily_goal">Daily Goal</label>
                    <input type="number" id="setting-daily-goal" min="1" max="50" value="5">
                </div>
                <button id="btn-save-settings" class="btn-primary" data-i18n="save">Save</button>
            </div>
        </div>
    </div>

    <script src="/js/i18n.js"></script>
    <script src="/js/tts.js"></script>
    <script src="/js/annotation.js"></script>
    <script src="/js/dictation.js"></script>
    <script src="/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create i18n.js**

Create `app/static/js/i18n.js`:

```javascript
const I18n = {
    lang: 'zh',
    strings: {
        zh: {
            login: '登录', register: '注册', login_subtitle: '通过丰富的句子分析掌握英语',
            vocabulary: '词汇', settings: '设置', logout: '退出',
            todays_progress: '今日进度', quick_review: '快速复习', all_levels: '所有级别',
            learn: '学习', read_aloud: '朗读', dictation: '听写',
            learn_hint: '学习句子结构，听发音。', read_aloud_hint: '听并跟读，评价你的发音。',
            dictation_hint: '输入你听到的内容：', submit: '提交',
            good: '好', okay: '一般', again: '再来',
            speed: '速度', repeat: '重复',
            all: '全部', mastered: '已掌握', learning: '学习中', weak: '薄弱',
            flashcard_mode: '闪卡模式', ui_language: 'UI语言', tts_speed: '语速',
            daily_goal: '每日目标', save: '保存',
            score: '得分', correct: '正确', close_match: '接近', missing: '缺少', extra: '多余',
            sentence: '句子', of: '/', lesson: '课程',
            flip: '翻转', next_card: '下一张',
        },
        vi: {
            login: 'Dang nhap', register: 'Dang ky', login_subtitle: 'Hoc tieng Anh voi phan tich cau phong phu',
            vocabulary: 'Tu vung', settings: 'Cai dat', logout: 'Dang xuat',
            todays_progress: 'Tien do hom nay', quick_review: 'On tap nhanh', all_levels: 'Tat ca cap do',
            learn: 'Hoc', read_aloud: 'Doc', dictation: 'Nghe viet',
            learn_hint: 'Hoc cau truc cau va nghe phat am.', read_aloud_hint: 'Nghe va lap lai. Danh gia phat am cua ban.',
            dictation_hint: 'Nhap nhung gi ban nghe duoc:', submit: 'Gui',
            good: 'Tot', okay: 'Duoc', again: 'Lai',
            speed: 'Toc do', repeat: 'Lap lai',
            all: 'Tat ca', mastered: 'Da thong thao', learning: 'Dang hoc', weak: 'Yeu',
            flashcard_mode: 'Che do the ghi nho', ui_language: 'Ngon ngu', tts_speed: 'Toc do doc',
            daily_goal: 'Muc tieu hang ngay', save: 'Luu',
            score: 'Diem', correct: 'Dung', close_match: 'Gan dung', missing: 'Thieu', extra: 'Thua',
            sentence: 'Cau', of: '/', lesson: 'Bai hoc',
            flip: 'Lat', next_card: 'The tiep theo',
        }
    },

    setLang(lang) {
        this.lang = lang;
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (this.strings[lang] && this.strings[lang][key]) {
                el.textContent = this.strings[lang][key];
            }
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            if (this.strings[lang] && this.strings[lang][key]) {
                el.title = this.strings[lang][key];
            }
        });
    },

    t(key) {
        return (this.strings[this.lang] && this.strings[this.lang][key]) || key;
    }
};
```

- [ ] **Step 3: Create app.js**

Create `app/static/js/app.js`:

```javascript
const App = {
    currentPage: 'login',
    currentLesson: null,
    currentSentenceIndex: 0,
    sentences: [],
    profile: null,

    async api(method, path, body) {
        const opts = { method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
        if (body) opts.body = JSON.stringify(body);
        const resp = await fetch(path, opts);
        if (resp.status === 401 && path !== '/api/auth/login') {
            this.showPage('login');
            return null;
        }
        return resp;
    },

    showPage(name) {
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        const page = document.getElementById('page-' + name);
        if (page) page.classList.add('active');
        this.currentPage = name;
    },

    async init() {
        this._bindLogin();
        this._bindDashboard();
        this._bindLesson();
        this._bindVocabulary();
        this._bindSettings();

        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                I18n.setLang(btn.dataset.lang);
            });
        });
    },

    _bindLogin() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.getElementById('login-form').style.display = btn.dataset.tab === 'login' ? 'block' : 'none';
                document.getElementById('register-form').style.display = btn.dataset.tab === 'register' ? 'block' : 'none';
            });
        });

        document.getElementById('register-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const lang = document.querySelector('.lang-btn.active')?.dataset.lang || 'zh';
            const resp = await this.api('POST', '/api/auth/register', {
                username: document.getElementById('reg-username').value,
                password: document.getElementById('reg-password').value,
                ui_language: lang,
            });
            if (resp && resp.ok) {
                document.querySelector('[data-tab="login"]').click();
                document.getElementById('login-username').value = document.getElementById('reg-username').value;
            } else {
                document.getElementById('reg-error').textContent = 'Username already exists';
            }
        });

        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const resp = await this.api('POST', '/api/auth/login', {
                username: document.getElementById('login-username').value,
                password: document.getElementById('login-password').value,
            });
            if (resp && resp.ok) {
                await this.loadDashboard();
            } else {
                document.getElementById('login-error').textContent = 'Invalid username or password';
            }
        });
    },

    async loadDashboard() {
        this.showPage('dashboard');
        const profileResp = await this.api('GET', '/api/user/profile');
        if (!profileResp) return;
        this.profile = await profileResp.json();
        I18n.setLang(this.profile.ui_language);

        document.getElementById('dash-username').textContent = this.profile.username;
        document.getElementById('dash-streak').textContent = this.profile.streak_days;
        document.getElementById('dash-xp').textContent = this.profile.xp;
        document.getElementById('dash-today').textContent = this.profile.sentences_today;
        document.getElementById('dash-goal').textContent = this.profile.daily_goal;

        const pct = Math.min(100, Math.round((this.profile.sentences_today / this.profile.daily_goal) * 100));
        document.getElementById('progress-pct').textContent = pct + '%';
        const circle = document.getElementById('progress-ring-fill');
        const circumference = 2 * Math.PI * 42;
        circle.style.strokeDasharray = circumference;
        circle.style.strokeDashoffset = circumference - (pct / 100) * circumference;

        const lessonsResp = await this.api('GET', '/api/lessons');
        if (!lessonsResp) return;
        const lessons = await lessonsResp.json();
        const grid = document.getElementById('lesson-grid');
        grid.innerHTML = '';
        const filterVal = document.getElementById('filter-difficulty').value;
        lessons.filter(l => filterVal === 'all' || l.difficulty === filterVal).forEach(l => {
            const lang = this.profile.ui_language;
            const title = lang === 'vi' ? l.title_vi : l.title_zh;
            const pctDone = l.sentence_count > 0 ? Math.round((l.completed_count / l.sentence_count) * 100) : 0;
            const card = document.createElement('div');
            card.className = 'lesson-card';
            card.innerHTML = `
                <div class="lesson-card-header">
                    <span class="lesson-num">${I18n.t('lesson')} ${l.id}</span>
                    <span class="difficulty-badge badge-${l.difficulty}">${l.difficulty}</span>
                </div>
                <div class="lesson-card-title">${title}</div>
                <div class="lesson-card-subtitle">${l.title}</div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width:${pctDone}%"></div>
                </div>
                <span class="progress-label">${l.completed_count}/${l.sentence_count}</span>
            `;
            card.addEventListener('click', () => this.openLesson(l.id));
            grid.appendChild(card);
        });
    },

    _bindDashboard() {
        document.getElementById('btn-logout').addEventListener('click', async () => {
            await this.api('POST', '/api/auth/logout');
            this.showPage('login');
        });
        document.getElementById('btn-vocab').addEventListener('click', () => this.openVocabulary());
        document.getElementById('btn-settings').addEventListener('click', () => this.openSettings());
        document.getElementById('btn-review').addEventListener('click', () => this.openReview());
        document.getElementById('filter-difficulty').addEventListener('change', () => this.loadDashboard());
    },

    async openLesson(lessonId) {
        const resp = await this.api('GET', `/api/lessons/${lessonId}`);
        if (!resp) return;
        const lesson = await resp.json();
        this.currentLesson = lesson;
        this.sentences = lesson.sentences;
        this.currentSentenceIndex = 0;
        const lang = this.profile.ui_language;
        const title = lang === 'vi' ? lesson.title_vi : lesson.title_zh;
        document.getElementById('lesson-title').textContent = `${title} (${lesson.title})`;
        this.showPage('lesson');
        this.renderSentence();
    },

    renderSentence() {
        const s = this.sentences[this.currentSentenceIndex];
        if (!s) return;
        document.getElementById('sentence-counter').textContent =
            `${this.currentSentenceIndex + 1}/${this.sentences.length}`;
        document.getElementById('nav-counter').textContent =
            `${this.currentSentenceIndex + 1} / ${this.sentences.length}`;

        const mode = document.querySelector('.mode-tab.active').dataset.mode;
        const showAnnotations = mode !== 'dictation';
        Annotation.render(document.getElementById('annotation-area'), s, this.profile.ui_language, showAnnotations);

        document.getElementById('dictation-input').value = '';
        document.getElementById('dictation-result').style.display = 'none';

        if (mode === 'learn') {
            TTS.speak(s.text);
        }
    },

    _bindLesson() {
        document.getElementById('btn-back').addEventListener('click', () => this.loadDashboard());
        document.getElementById('btn-prev').addEventListener('click', () => {
            if (this.currentSentenceIndex > 0) {
                this.currentSentenceIndex--;
                this.renderSentence();
            }
        });
        document.getElementById('btn-next').addEventListener('click', () => {
            if (this.currentSentenceIndex < this.sentences.length - 1) {
                this.currentSentenceIndex++;
                this.renderSentence();
            }
        });
        document.getElementById('btn-play').addEventListener('click', () => {
            const s = this.sentences[this.currentSentenceIndex];
            if (s) TTS.speak(s.text);
        });
        document.getElementById('btn-repeat').addEventListener('click', () => {
            const s = this.sentences[this.currentSentenceIndex];
            if (s) TTS.speak(s.text);
        });
        document.getElementById('speed-slider').addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            document.getElementById('speed-value').textContent = val.toFixed(1) + 'x';
            TTS.setSpeed(val);
        });

        document.querySelectorAll('.mode-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                document.querySelectorAll('.mode-panel').forEach(p => p.classList.remove('active'));
                const mode = tab.dataset.mode;
                const panelId = { learn: 'mode-learn', read_aloud: 'mode-read-aloud', dictation: 'mode-dictation' }[mode];
                document.getElementById(panelId).classList.add('active');
                this.renderSentence();
            });
        });

        document.querySelectorAll('.rate-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const s = this.sentences[this.currentSentenceIndex];
                await this.api('POST', '/api/practice/self-rate', { sentence_id: s.id, rating: btn.dataset.rating });
                if (this.currentSentenceIndex < this.sentences.length - 1) {
                    this.currentSentenceIndex++;
                    this.renderSentence();
                }
            });
        });

        document.getElementById('btn-submit-dictation').addEventListener('click', async () => {
            const s = this.sentences[this.currentSentenceIndex];
            const typed = document.getElementById('dictation-input').value;
            const resp = await this.api('POST', '/api/practice/submit', { sentence_id: s.id, typed_text: typed });
            if (!resp) return;
            const result = await resp.json();
            Dictation.showResult(result, this.profile.ui_language);
            Annotation.render(document.getElementById('annotation-area'), s, this.profile.ui_language, true);
        });
    },

    async openVocabulary() {
        this.showPage('vocabulary');
        const filter = document.getElementById('vocab-filter-select').value;
        const resp = await this.api('GET', `/api/vocabulary?filter=${filter}`);
        if (!resp) return;
        const words = await resp.json();
        const list = document.getElementById('vocab-list');
        list.innerHTML = '';
        words.forEach(w => {
            const item = document.createElement('div');
            item.className = 'vocab-item';
            item.innerHTML = `
                <span class="vocab-word">${w.word}</span>
                <span class="vocab-ipa">${w.ipa}</span>
                <span class="pos-badge pos-${w.pos}">${w.pos}</span>
                <span class="vocab-status status-${w.status}">${I18n.t(w.status)}</span>
                <span class="vocab-stats">${w.correct_count}/${w.seen_count}</span>
            `;
            list.appendChild(item);
        });
    },

    _bindVocabulary() {
        document.getElementById('vocab-back').addEventListener('click', () => this.loadDashboard());
        document.getElementById('vocab-filter-select').addEventListener('change', () => this.openVocabulary());
        document.getElementById('btn-flashcards').addEventListener('click', async () => {
            const resp = await this.api('GET', '/api/vocabulary/flashcards');
            if (!resp) return;
            const cards = await resp.json();
            Dictation.showFlashcards(cards, this.profile.ui_language);
        });
    },

    async openSettings() {
        this.showPage('settings');
        if (this.profile) {
            document.getElementById('setting-language').value = this.profile.ui_language;
            document.getElementById('setting-tts-speed').value = this.profile.tts_speed;
            document.getElementById('setting-speed-val').textContent = this.profile.tts_speed.toFixed(1) + 'x';
            document.getElementById('setting-daily-goal').value = this.profile.daily_goal;
        }
    },

    _bindSettings() {
        document.getElementById('settings-back').addEventListener('click', () => this.loadDashboard());
        document.getElementById('setting-tts-speed').addEventListener('input', (e) => {
            document.getElementById('setting-speed-val').textContent = parseFloat(e.target.value).toFixed(1) + 'x';
        });
        document.getElementById('btn-save-settings').addEventListener('click', async () => {
            await this.api('PUT', '/api/user/settings', {
                ui_language: document.getElementById('setting-language').value,
                tts_speed: parseFloat(document.getElementById('setting-tts-speed').value),
                daily_goal: parseInt(document.getElementById('setting-daily-goal').value),
            });
            const profileResp = await this.api('GET', '/api/user/profile');
            if (profileResp) {
                this.profile = await profileResp.json();
                I18n.setLang(this.profile.ui_language);
                TTS.setSpeed(this.profile.tts_speed);
            }
            this.loadDashboard();
        });
    },

    async openReview() {
        const resp = await this.api('GET', '/api/review/due');
        if (!resp) return;
        const items = await resp.json();
        if (items.length === 0) return;
        const first = items[0];
        const lessonId = parseInt(first.sentence_id.split('-')[0]);
        await this.openLesson(lessonId);
        const idx = this.sentences.findIndex(s => s.id === first.sentence_id);
        if (idx >= 0) {
            this.currentSentenceIndex = idx;
            this.renderSentence();
        }
    },
};

document.addEventListener('DOMContentLoaded', () => App.init());
```

- [ ] **Step 4: Verify the file loads without syntax errors**

```bash
python -c "
from pathlib import Path
for f in ['index.html', 'js/app.js', 'js/i18n.js']:
    p = Path('app/static') / f
    assert p.exists(), f'{f} missing'
    print(f'{f}: {p.stat().st_size} bytes')
print('All frontend shell files OK')
"
```

- [ ] **Step 5: Commit**

```bash
git add app/static/index.html app/static/js/app.js app/static/js/i18n.js
git commit -m "feat: add SPA shell with router, i18n, and all page layouts"
```

---

### Task 13: Frontend - TTS Module

**Files:**
- Create: `app/static/js/tts.js`

- [ ] **Step 1: Create tts.js**

Create `app/static/js/tts.js`:

```javascript
const TTS = {
    speed: 1.0,
    utterance: null,
    wordSpans: [],

    setSpeed(rate) {
        this.speed = Math.max(0.5, Math.min(2.0, rate));
    },

    speak(text) {
        if (!('speechSynthesis' in window)) return;
        speechSynthesis.cancel();

        this.utterance = new SpeechSynthesisUtterance(text);
        this.utterance.rate = this.speed;
        this.utterance.lang = 'en-US';

        const voices = speechSynthesis.getVoices();
        const preferred = voices.find(v => v.name.includes('Google US English'))
            || voices.find(v => v.name.includes('Google UK English'))
            || voices.find(v => v.lang === 'en-US' && (v.name.includes('enhanced') || v.name.includes('premium')))
            || voices.find(v => v.lang.startsWith('en'));
        if (preferred) this.utterance.voice = preferred;

        this.wordSpans = document.querySelectorAll('.word-text');

        this.utterance.onboundary = (event) => {
            if (event.name !== 'word') return;
            this._clearHighlights();
            const charIdx = event.charIndex;
            this.wordSpans.forEach(span => {
                const offset = parseInt(span.dataset.charOffset || '0');
                const word = span.textContent;
                if (charIdx >= offset && charIdx < offset + word.length) {
                    span.classList.add('tts-highlight');
                }
            });
        };

        this.utterance.onend = () => this._clearHighlights();
        this.utterance.onerror = () => this._clearHighlights();

        speechSynthesis.speak(this.utterance);
    },

    stop() {
        speechSynthesis.cancel();
        this._clearHighlights();
    },

    _clearHighlights() {
        this.wordSpans.forEach(span => span.classList.remove('tts-highlight'));
    }
};

if ('speechSynthesis' in window) {
    speechSynthesis.getVoices();
    speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/tts.js
git commit -m "feat: add TTS module with word-by-word highlighting"
```

---

### Task 14: Frontend - Annotation Renderer

**Files:**
- Create: `app/static/js/annotation.js`

- [ ] **Step 1: Create annotation.js**

Create `app/static/js/annotation.js`:

```javascript
const Annotation = {
    POS_COLORS: {
        noun: '#2196F3', verb: '#F44336', pronoun: '#9C27B0',
        adjective: '#FF9800', adverb: '#4CAF50', preposition: '#607D8B',
        particle: '#00BCD4', interjection: '#795548', determiner: '#3F51B5',
        conjunction: '#E91E63',
    },

    render(container, sentence, lang, showAnnotations) {
        container.innerHTML = '';
        if (!sentence || !sentence.words) return;

        if (showAnnotations) {
            const wordsRow = document.createElement('div');
            wordsRow.className = 'words-row';

            let charOffset = 0;
            sentence.words.forEach((w, i) => {
                const unit = document.createElement('div');
                unit.className = 'word-unit';

                const ipa = document.createElement('span');
                ipa.className = 'word-ipa';
                ipa.textContent = w.ipa;

                const posKey = `pos_${lang}`;
                const posBadge = document.createElement('span');
                posBadge.className = `pos-badge`;
                posBadge.style.backgroundColor = this.POS_COLORS[w.pos] || '#757575';
                posBadge.textContent = w[posKey] || w.pos;

                const wordSpan = document.createElement('span');
                wordSpan.className = 'word-text';
                wordSpan.textContent = w.word;
                wordSpan.dataset.charOffset = charOffset;
                wordSpan.dataset.group = w.group;

                unit.appendChild(ipa);
                unit.appendChild(posBadge);
                unit.appendChild(wordSpan);
                wordsRow.appendChild(unit);

                charOffset += w.word.length + 1;
            });
            container.appendChild(wordsRow);

            if (sentence.constituents && sentence.constituents.length > 0) {
                const bracketsDiv = document.createElement('div');
                bracketsDiv.className = 'constituents-row';

                sentence.constituents.forEach(c => {
                    const group = document.createElement('div');
                    group.className = 'constituent-group';
                    group.style.borderColor = c.color;

                    const labelKey = `label_${lang}`;
                    const label = document.createElement('span');
                    label.className = 'constituent-label';
                    label.style.color = c.color;
                    label.textContent = c[labelKey] || c.label_en;

                    const wordsInGroup = c.word_indices.map(idx => sentence.words[idx]?.word || '').join(' ');
                    const bracket = document.createElement('span');
                    bracket.className = 'constituent-bracket';
                    bracket.style.borderBottomColor = c.color;
                    bracket.textContent = wordsInGroup;

                    group.appendChild(bracket);
                    group.appendChild(label);
                    bracketsDiv.appendChild(group);
                });
                container.appendChild(bracketsDiv);
            }

            const translationKey = `translation_${lang}`;
            const translation = document.createElement('div');
            translation.className = 'translation';
            translation.textContent = sentence[translationKey] || '';
            container.appendChild(translation);
        } else {
            const hidden = document.createElement('div');
            hidden.className = 'dictation-mode-text';
            hidden.innerHTML = '<span class="listen-icon">&#128266;</span> <span class="listen-text">' +
                I18n.t('dictation_hint') + '</span>';
            container.appendChild(hidden);
        }
    }
};
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/annotation.js
git commit -m "feat: add sentence annotation renderer with POS badges and constituents"
```

---

### Task 15: Frontend - Dictation Module

**Files:**
- Create: `app/static/js/dictation.js`

- [ ] **Step 1: Create dictation.js**

Create `app/static/js/dictation.js`:

```javascript
const Dictation = {
    isComposing: false,

    init() {
        const input = document.getElementById('dictation-input');
        if (!input) return;
        input.addEventListener('compositionstart', () => { this.isComposing = true; });
        input.addEventListener('compositionend', () => { this.isComposing = false; });
    },

    showResult(result, lang) {
        const container = document.getElementById('dictation-result');
        container.style.display = 'block';
        container.innerHTML = '';

        const scoreLine = document.createElement('div');
        scoreLine.className = 'score-line';
        const pct = Math.round(result.score * 100);
        scoreLine.innerHTML = `<span class="score-label">${I18n.t('score')}:</span> <span class="score-value score-${pct >= 70 ? 'good' : pct >= 40 ? 'okay' : 'bad'}">${pct}%</span>`;
        if (result.xp_earned > 0) {
            scoreLine.innerHTML += ` <span class="xp-earned">+${result.xp_earned} XP</span>`;
        }
        container.appendChild(scoreLine);

        const diffLine = document.createElement('div');
        diffLine.className = 'diff-line';
        result.diffs.forEach(d => {
            const span = document.createElement('span');
            span.className = `diff-word diff-${d.status}`;
            span.textContent = d.word;
            if (d.status === 'close' && d.expected) {
                span.title = `${I18n.t('close_match')}: ${d.expected}`;
            } else if (d.status === 'missing') {
                span.title = I18n.t('missing');
            } else if (d.status === 'extra') {
                span.title = I18n.t('extra');
            }
            diffLine.appendChild(span);
            diffLine.appendChild(document.createTextNode(' '));
        });
        container.appendChild(diffLine);

        const expectedLine = document.createElement('div');
        expectedLine.className = 'expected-line';
        expectedLine.innerHTML = `<strong>${I18n.t('correct')}:</strong> ${result.expected_text}`;
        container.appendChild(expectedLine);
    },

    showFlashcards(cards, lang) {
        const area = document.getElementById('flashcard-area');
        area.style.display = 'block';
        area.innerHTML = '';

        if (cards.length === 0) {
            area.innerHTML = '<p>No vocabulary words yet.</p>';
            return;
        }

        let idx = 0;
        const renderCard = () => {
            if (idx >= cards.length) {
                area.innerHTML = '<p>All cards reviewed!</p>';
                return;
            }
            const c = cards[idx];
            const translationKey = `translation_${lang}`;
            area.innerHTML = `
                <div class="flashcard">
                    <div class="flashcard-front">
                        <span class="fc-word">${c.word}</span>
                        <span class="fc-ipa">${c.ipa}</span>
                        <span class="fc-pos">${c.pos}</span>
                    </div>
                    <div class="flashcard-back" style="display:none">
                        <span class="fc-example">${c.example_sentence}</span>
                        <span class="fc-translation">${c[translationKey] || ''}</span>
                    </div>
                    <div class="flashcard-actions">
                        <button class="btn-flip btn-primary">${I18n.t('flip')}</button>
                        <button class="btn-next-card btn-primary" style="display:none">${I18n.t('next_card')}</button>
                    </div>
                </div>
            `;
            area.querySelector('.btn-flip').addEventListener('click', () => {
                area.querySelector('.flashcard-back').style.display = 'block';
                area.querySelector('.btn-flip').style.display = 'none';
                area.querySelector('.btn-next-card').style.display = 'inline-block';
            });
            area.querySelector('.btn-next-card').addEventListener('click', () => {
                idx++;
                renderCard();
            });
        };
        renderCard();
    }
};

document.addEventListener('DOMContentLoaded', () => Dictation.init());
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/dictation.js
git commit -m "feat: add dictation module with IME handling, diff display, and flashcards"
```

---

### Task 16: Frontend - CSS Styles

**Files:**
- Create: `app/static/css/style.css`

- [ ] **Step 1: Create style.css**

Create `app/static/css/style.css`:

```css
:root {
    --bg: #f5f5f0;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --text-secondary: #666;
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --success: #16a34a;
    --warning: #eab308;
    --danger: #dc2626;
    --border: #e5e5e5;
    --radius: 12px;
    --shadow: 0 2px 8px rgba(0,0,0,0.08);
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    min-height: 100vh;
}

.page { display: none; min-height: 100vh; }
.page.active { display: block; }

/* Login */
.login-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    padding: 2rem;
}
.login-title { text-align: center; margin-bottom: 0.5rem; }
.title-en { display: block; font-size: 2rem; font-weight: 700; color: var(--primary); }
.title-zh, .title-vi { display: block; font-size: 1rem; color: var(--text-secondary); }
.login-subtitle { text-align: center; color: var(--text-secondary); margin-bottom: 1.5rem; }
.lang-selector { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
.lang-btn {
    padding: 0.4rem 1rem;
    border: 2px solid var(--border);
    border-radius: 20px;
    background: var(--card-bg);
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
}
.lang-btn.active { border-color: var(--primary); color: var(--primary); font-weight: 600; }
.tab-bar { display: flex; gap: 0; margin-bottom: 1rem; }
.tab-btn {
    flex: 1;
    padding: 0.6rem;
    border: none;
    background: var(--border);
    cursor: pointer;
    font-size: 0.95rem;
    transition: all 0.2s;
}
.tab-btn:first-child { border-radius: var(--radius) 0 0 var(--radius); }
.tab-btn:last-child { border-radius: 0 var(--radius) var(--radius) 0; }
.tab-btn.active { background: var(--primary); color: white; }
.auth-form { width: 100%; max-width: 320px; }
.auth-form input {
    width: 100%;
    padding: 0.75rem 1rem;
    margin-bottom: 0.75rem;
    border: 2px solid var(--border);
    border-radius: var(--radius);
    font-size: 1rem;
    outline: none;
    transition: border-color 0.2s;
}
.auth-form input:focus { border-color: var(--primary); }
.error-msg { color: var(--danger); font-size: 0.85rem; margin-top: 0.5rem; text-align: center; }

/* Buttons */
.btn-primary {
    display: block;
    width: 100%;
    padding: 0.75rem;
    background: var(--primary);
    color: white;
    border: none;
    border-radius: var(--radius);
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}
.btn-primary:hover { background: var(--primary-hover); }
.icon-btn {
    background: none;
    border: none;
    font-size: 1.3rem;
    cursor: pointer;
    padding: 0.3rem;
    opacity: 0.7;
    transition: opacity 0.2s;
}
.icon-btn:hover { opacity: 1; }

/* Top Bar */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: var(--card-bg);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 10;
}
.stats-bar { display: flex; gap: 1rem; font-size: 0.9rem; }
.stat-item { display: flex; align-items: center; gap: 0.25rem; }
.flame { font-size: 1.1rem; }
.top-actions { display: flex; gap: 0.5rem; }

/* Dashboard */
.dashboard-content { padding: 1rem; }
.progress-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 1.25rem;
    box-shadow: var(--shadow);
    margin-bottom: 1rem;
}
.progress-ring-container { position: relative; }
.progress-ring-bg { fill: none; stroke: var(--border); stroke-width: 6; }
.progress-ring-fill {
    fill: none;
    stroke: var(--primary);
    stroke-width: 6;
    stroke-linecap: round;
    transform: rotate(-90deg);
    transform-origin: 50% 50%;
    transition: stroke-dashoffset 0.5s ease;
}
.progress-pct {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 1.1rem;
    font-weight: 700;
}
.btn-review {
    width: 100%;
    padding: 0.7rem;
    background: var(--success);
    color: white;
    border: none;
    border-radius: var(--radius);
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    margin-bottom: 1rem;
}
.filter-bar { margin-bottom: 1rem; }
.filter-bar select {
    padding: 0.5rem 1rem;
    border: 2px solid var(--border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    background: var(--card-bg);
}

/* Lesson Grid */
.lesson-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem; }
.lesson-card {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 1rem;
    box-shadow: var(--shadow);
    cursor: pointer;
    transition: transform 0.15s, box-shadow 0.15s;
}
.lesson-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
.lesson-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.lesson-num { font-size: 0.8rem; color: var(--text-secondary); }
.difficulty-badge {
    padding: 0.15rem 0.5rem;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
}
.badge-A1 { background: #4CAF50; }
.badge-A2 { background: #8BC34A; }
.badge-B1 { background: #FF9800; }
.badge-B2 { background: #F44336; }
.badge-C1 { background: #9C27B0; }
.badge-C2 { background: #673AB7; }
.lesson-card-title { font-size: 1.05rem; font-weight: 600; }
.lesson-card-subtitle { font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem; }
.progress-bar-container {
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    margin-bottom: 0.25rem;
}
.progress-bar-fill { height: 100%; background: var(--primary); border-radius: 3px; transition: width 0.3s; }
.progress-label { font-size: 0.8rem; color: var(--text-secondary); }

/* Lesson View */
.lesson-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: var(--card-bg);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 10;
}
.lesson-title-text { font-weight: 600; flex: 1; }
.sentence-counter { font-size: 0.85rem; color: var(--text-secondary); }

/* Annotation Area */
.annotation-area {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin: 1rem;
    box-shadow: var(--shadow);
    min-height: 150px;
}
.words-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    justify-content: center;
    align-items: flex-end;
    margin-bottom: 1rem;
}
.word-unit {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.3rem;
}
.word-ipa {
    font-size: 0.8rem;
    color: var(--text-secondary);
    font-family: 'Lucida Sans Unicode', 'DejaVu Sans', sans-serif;
}
.pos-badge {
    font-size: 0.65rem;
    color: white;
    padding: 0.1rem 0.4rem;
    border-radius: 8px;
    font-weight: 600;
    white-space: nowrap;
}
.word-text {
    font-size: 1.6rem;
    font-weight: 700;
    transition: color 0.15s, background 0.15s;
    padding: 0.1rem 0.3rem;
    border-radius: 4px;
}
.word-text.tts-highlight {
    background: #fef3c7;
    color: var(--primary);
}

/* Constituents */
.constituents-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    justify-content: center;
    margin-bottom: 1rem;
    padding-top: 0.5rem;
}
.constituent-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.2rem;
}
.constituent-bracket {
    border-bottom: 3px solid;
    padding: 0.2rem 0.5rem;
    font-size: 0.9rem;
    color: var(--text-secondary);
}
.constituent-label {
    font-size: 0.75rem;
    font-weight: 600;
}

/* Translation */
.translation {
    text-align: center;
    font-size: 1.1rem;
    color: var(--text-secondary);
    margin-top: 0.5rem;
    padding-top: 0.75rem;
    border-top: 1px solid var(--border);
}

/* Dictation mode */
.dictation-mode-text {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 2rem;
    font-size: 1.2rem;
    color: var(--text-secondary);
}
.listen-icon { font-size: 2rem; }

/* Audio Controls */
.audio-controls {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    justify-content: center;
}
.play-btn { font-size: 1.5rem; }
.speed-control {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
}
.speed-control input[type="range"] { width: 80px; }

/* Mode Tabs */
.mode-tabs {
    display: flex;
    border-bottom: 2px solid var(--border);
    margin: 0 1rem;
}
.mode-tab {
    flex: 1;
    padding: 0.65rem;
    text-align: center;
    border: none;
    background: none;
    cursor: pointer;
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--text-secondary);
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
}
.mode-tab.active { color: var(--primary); border-bottom-color: var(--primary); }

/* Mode Content */
.mode-content { padding: 1rem; }
.mode-panel { display: none; }
.mode-panel.active { display: block; }
.mode-hint { color: var(--text-secondary); margin-bottom: 0.75rem; font-size: 0.9rem; }
.rate-buttons { display: flex; gap: 0.75rem; }
.rate-btn {
    flex: 1;
    padding: 0.7rem;
    border: 2px solid;
    border-radius: var(--radius);
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    background: var(--card-bg);
    transition: all 0.2s;
}
.rate-good { border-color: var(--success); color: var(--success); }
.rate-good:hover { background: var(--success); color: white; }
.rate-okay { border-color: var(--warning); color: #a16207; }
.rate-okay:hover { background: var(--warning); color: white; }
.rate-again { border-color: var(--danger); color: var(--danger); }
.rate-again:hover { background: var(--danger); color: white; }

/* Dictation */
.dictation-input {
    width: 100%;
    padding: 0.75rem;
    border: 2px solid var(--border);
    border-radius: var(--radius);
    font-size: 1.1rem;
    resize: none;
    outline: none;
    margin-bottom: 0.75rem;
    transition: border-color 0.2s;
}
.dictation-input:focus { border-color: var(--primary); }
.dictation-result {
    background: var(--bg);
    border-radius: var(--radius);
    padding: 1rem;
    margin-top: 1rem;
}
.score-line { margin-bottom: 0.75rem; font-size: 1.1rem; }
.score-value { font-weight: 700; font-size: 1.3rem; }
.score-good { color: var(--success); }
.score-okay { color: #a16207; }
.score-bad { color: var(--danger); }
.xp-earned { color: var(--primary); font-weight: 600; }
.diff-line { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.75rem; }
.diff-word {
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-size: 1rem;
}
.diff-correct { background: #dcfce7; color: #166534; }
.diff-close { background: #fef9c3; color: #854d0e; }
.diff-incorrect { background: #fee2e2; color: #991b1b; }
.diff-missing { background: #fee2e2; color: #991b1b; text-decoration: line-through; }
.diff-extra { background: #fed7aa; color: #9a3412; }
.expected-line { font-size: 0.9rem; color: var(--text-secondary); }

/* Sentence Nav */
.sentence-nav {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 2rem;
    padding: 1rem;
    border-top: 1px solid var(--border);
}
.nav-btn {
    padding: 0.5rem 1.5rem;
    border: 2px solid var(--border);
    border-radius: var(--radius);
    background: var(--card-bg);
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.2s;
}
.nav-btn:hover { border-color: var(--primary); color: var(--primary); }
.nav-counter { font-weight: 600; color: var(--text-secondary); }

/* Vocabulary */
.vocab-list { padding: 0 1rem; }
.vocab-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid var(--border);
}
.vocab-word { font-weight: 600; min-width: 80px; }
.vocab-ipa { font-size: 0.85rem; color: var(--text-secondary); min-width: 80px; }
.vocab-status { font-size: 0.8rem; padding: 0.15rem 0.5rem; border-radius: 10px; }
.status-mastered { background: #dcfce7; color: #166534; }
.status-learning { background: #fef9c3; color: #854d0e; }
.status-weak { background: #fee2e2; color: #991b1b; }
.vocab-stats { font-size: 0.8rem; color: var(--text-secondary); margin-left: auto; }
.vocab-filter { display: flex; gap: 0.5rem; }
.vocab-filter select { padding: 0.3rem 0.75rem; border-radius: var(--radius); border: 1px solid var(--border); }

/* Flashcards */
.flashcard-area { padding: 1rem; }
.flashcard {
    background: var(--card-bg);
    border-radius: var(--radius);
    padding: 2rem;
    box-shadow: var(--shadow);
    text-align: center;
    min-height: 200px;
}
.flashcard-front { margin-bottom: 1rem; }
.fc-word { display: block; font-size: 2rem; font-weight: 700; }
.fc-ipa { display: block; font-size: 1rem; color: var(--text-secondary); margin-top: 0.5rem; }
.fc-pos { display: block; font-size: 0.85rem; color: var(--primary); margin-top: 0.25rem; }
.flashcard-back { padding: 1rem 0; border-top: 1px solid var(--border); }
.fc-example { display: block; font-size: 1rem; font-style: italic; margin-bottom: 0.5rem; }
.fc-translation { display: block; font-size: 1.1rem; font-weight: 600; color: var(--primary); }
.flashcard-actions { display: flex; gap: 0.75rem; margin-top: 1rem; }
.flashcard-actions .btn-primary { flex: 1; }

/* Settings */
.settings-form { padding: 1rem; }
.setting-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 0;
    border-bottom: 1px solid var(--border);
}
.setting-item label { font-weight: 500; }
.setting-item select, .setting-item input[type="number"] {
    padding: 0.4rem 0.75rem;
    border: 2px solid var(--border);
    border-radius: var(--radius);
    font-size: 0.95rem;
}
.setting-item input[type="range"] { width: 120px; }

/* Responsive */
@media (max-width: 480px) {
    .word-text { font-size: 1.2rem; }
    .words-row { gap: 0.4rem; }
    .lesson-grid { grid-template-columns: 1fr; }
    .stats-bar { gap: 0.5rem; font-size: 0.8rem; }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/css/style.css
git commit -m "feat: add complete CSS styles for all pages"
```

---

### Task 17: End-to-End Smoke Test

**Files:**
- No new files — verify everything works together

- [ ] **Step 1: Import lesson data**

```bash
cd /fsx-neo/dedicated-fsx-data-repo-neo-us-east-1/toyng/toyng_ws/projects/Personalized_Product_search/englisht_turorial
python -m tools.import_lessons
```

Expected: 3 lessons imported

- [ ] **Step 2: Run all backend tests**

```bash
python -m pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 3: Start the dev server**

```bash
cd /fsx-neo/dedicated-fsx-data-repo-neo-us-east-1/toyng/toyng_ws/projects/Personalized_Product_search/englisht_turorial
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

- [ ] **Step 4: Manual browser testing checklist**

Open browser to `http://localhost:8080` and test:

1. **Login page:** Language toggle works, register a new account, login
2. **Dashboard:** Shows lesson cards, streak/XP, progress ring
3. **Lesson view:** Click a lesson, see annotated sentence with IPA, POS badges, constituent brackets, translation
4. **TTS:** Click play, words highlight as spoken, speed slider works
5. **Mode tabs:** Switch between Learn/Read Aloud/Dictation
6. **Dictation:** Type a sentence, submit, see diff highlighting and score
7. **Read Aloud:** Self-rate buttons work
8. **Navigation:** Prev/next arrows work through sentences
9. **Vocabulary:** Shows words after practicing, filter works
10. **Settings:** Change language, speed, daily goal — saved correctly

- [ ] **Step 5: Fix any issues found during testing**

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete English learning app with all features working"
```
