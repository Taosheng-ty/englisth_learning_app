"""Comprehensive tests for vocabulary and flashcard flows.

Covers 17 test scenarios:
 1. Empty vocabulary for new user
 2. Vocabulary populated after practice
 3. Word fields present on each vocab entry
 4. Status calculation (mastered / learning / weak)
 5. Filter mastered
 6. Filter learning
 7. Filter weak
 8. Filter all
 9. Seen count increments on repeated submission
10. Correct count increments only on correct dictation
11. Flashcards endpoint returns cards ordered by weakness
12. Flashcard fields present on each card
13. Flashcard ordering (weakest first)
14. Flashcards limit (max 20)
15. Empty flashcards for new user with no vocab
16. Auth required (401 without login)
17. Multiple users have independent vocabulary lists
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.database import init_db

# ---------------------------------------------------------------------------
# Path to real lesson JSON files shipped with the project
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = PROJECT_ROOT / "data" / "lessons"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp_db() -> Path:
    """Return a fresh temp-file path for an SQLite DB."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return Path(f.name)


def _import_lesson(conn: sqlite3.Connection, filepath: Path):
    """Import a single lesson JSON into *conn* (mirrors tools/import_lessons.py)."""
    with open(filepath) as fh:
        data = json.load(fh)
    conn.execute(
        "INSERT OR REPLACE INTO lessons "
        "(id, title, title_zh, title_vi, difficulty, category, sentence_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["id"], data["title"], data["title_zh"], data["title_vi"],
         data["difficulty"], data["category"], len(data["sentences"])),
    )
    for s in data["sentences"]:
        sid = f"{data['id']}-{s['index']:02d}"
        conn.execute(
            "INSERT OR REPLACE INTO sentences "
            "(id, lesson_id, idx, text, translation_zh, translation_vi, words_json, constituents_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, data["id"], s["index"], s["text"],
             s["translation_zh"], s["translation_vi"],
             json.dumps(s["words"]), json.dumps(s["constituents"])),
        )
    conn.commit()


def _seed_lessons(db_path: Path, lesson_files: list[str] | None = None):
    """Seed lessons from JSON files into the database.

    *lesson_files*: list of filenames like ``["lesson_001.json", "lesson_002.json"]``.
    If ``None``, seed lesson_001 and lesson_002.
    """
    if lesson_files is None:
        lesson_files = ["lesson_001.json", "lesson_002.json"]
    conn = sqlite3.connect(str(db_path))
    for name in lesson_files:
        fp = LESSONS_DIR / name
        assert fp.exists(), f"Lesson file not found: {fp}"
        _import_lesson(conn, fp)
    conn.close()


def _make_app_seeded(lesson_files: list[str] | None = None):
    """Create a fresh app + TestClient with seeded lesson data."""
    db_path = _tmp_db()
    init_db(db_path)
    _seed_lessons(db_path, lesson_files)
    app = create_app(db_path)
    client = TestClient(app)
    return client, db_path


def _register_and_login(client: TestClient, username: str = "alice", password: str = "pass123"):
    """Register + login; returns the client (cookies are set automatically)."""
    client.post("/api/auth/register", json={"username": username, "password": password})
    client.post("/api/auth/login", json={"username": username, "password": password})
    return client


def _fresh_authed_client(lesson_files: list[str] | None = None, username: str = "alice"):
    """Convenience: app + seeded lessons + registered & logged-in user."""
    client, db_path = _make_app_seeded(lesson_files)
    _register_and_login(client, username)
    return client, db_path


def _inject_vocab(db_path: Path, user_id: int, entries: list[dict]):
    """Directly insert vocabulary rows to set up specific seen/correct counts."""
    conn = sqlite3.connect(str(db_path))
    for e in entries:
        conn.execute(
            "INSERT OR REPLACE INTO vocabulary "
            "(user_id, word, ipa, pos, seen_count, correct_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, e["word"], e.get("ipa", ""), e.get("pos", ""),
             e["seen_count"], e["correct_count"]),
        )
    conn.commit()
    conn.close()


# ===================================================================
# 1. Empty vocabulary for a new user
# ===================================================================

class TestEmptyVocabulary:
    def test_new_user_has_empty_vocabulary(self):
        client, db_path = _fresh_authed_client()
        resp = client.get("/api/vocabulary")
        assert resp.status_code == 200
        assert resp.json() == []
        db_path.unlink()


# ===================================================================
# 2. Vocabulary populated after practice
# ===================================================================

class TestVocabularyAfterPractice:
    def test_vocab_populated_after_dictation(self):
        """Submit a dictation for sentence 1-01 ('Hi Min, you look gorgeous.')
        and verify all words appear in the vocabulary list."""
        client, db_path = _fresh_authed_client()
        # Sentence 1-01: "Hi Min, you look gorgeous."
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        resp = client.get("/api/vocabulary")
        assert resp.status_code == 200
        data = resp.json()
        vocab_words = {entry["word"] for entry in data}
        for expected in ["hi", "min", "you", "look", "gorgeous"]:
            assert expected in vocab_words, f"'{expected}' not found in vocabulary"
        db_path.unlink()


# ===================================================================
# 3. Word fields present on each vocabulary entry
# ===================================================================

class TestWordFields:
    def test_each_entry_has_required_fields(self):
        client, db_path = _fresh_authed_client()
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        resp = client.get("/api/vocabulary")
        data = resp.json()
        required_fields = {"word", "ipa", "pos", "seen_count", "correct_count", "status"}
        for entry in data:
            assert required_fields.issubset(entry.keys()), (
                f"Missing fields in {entry}: {required_fields - entry.keys()}"
            )
        db_path.unlink()


# ===================================================================
# 4. Status calculation
# ===================================================================

class TestStatusCalculation:
    def test_mastered_status(self):
        """correct_count / seen_count >= 0.8 => mastered."""
        client, db_path = _fresh_authed_client()
        # Inject vocabulary directly: 10 seen, 8 correct => ratio 0.8
        _inject_vocab(db_path, 1, [
            {"word": "testword", "seen_count": 10, "correct_count": 8},
        ])
        resp = client.get("/api/vocabulary")
        entry = [e for e in resp.json() if e["word"] == "testword"][0]
        assert entry["status"] == "mastered"
        db_path.unlink()

    def test_learning_status(self):
        """0.4 <= ratio < 0.8 => learning."""
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "studyword", "seen_count": 10, "correct_count": 5},
        ])
        resp = client.get("/api/vocabulary")
        entry = [e for e in resp.json() if e["word"] == "studyword"][0]
        assert entry["status"] == "learning"
        db_path.unlink()

    def test_weak_status(self):
        """ratio < 0.4 => weak."""
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "hardword", "seen_count": 10, "correct_count": 2},
        ])
        resp = client.get("/api/vocabulary")
        entry = [e for e in resp.json() if e["word"] == "hardword"][0]
        assert entry["status"] == "weak"
        db_path.unlink()

    def test_zero_seen_is_weak(self):
        """seen_count == 0 => ratio 0 => weak."""
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "zeroword", "seen_count": 0, "correct_count": 0},
        ])
        resp = client.get("/api/vocabulary")
        entry = [e for e in resp.json() if e["word"] == "zeroword"][0]
        assert entry["status"] == "weak"
        db_path.unlink()

    def test_boundary_mastered_exactly_0_8(self):
        """ratio == 0.8 should be mastered."""
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "edgeword", "seen_count": 5, "correct_count": 4},
        ])
        resp = client.get("/api/vocabulary")
        entry = [e for e in resp.json() if e["word"] == "edgeword"][0]
        assert entry["status"] == "mastered"
        db_path.unlink()

    def test_boundary_learning_exactly_0_4(self):
        """ratio == 0.4 should be learning."""
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "midword", "seen_count": 5, "correct_count": 2},
        ])
        resp = client.get("/api/vocabulary")
        entry = [e for e in resp.json() if e["word"] == "midword"][0]
        assert entry["status"] == "learning"
        db_path.unlink()


# ===================================================================
# 5. Filter mastered
# ===================================================================

class TestFilterMastered:
    def test_filter_mastered_returns_only_mastered(self):
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "alpha", "seen_count": 10, "correct_count": 9},   # mastered
            {"word": "beta",  "seen_count": 10, "correct_count": 5},   # learning
            {"word": "gamma", "seen_count": 10, "correct_count": 1},   # weak
        ])
        resp = client.get("/api/vocabulary?filter=mastered")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["word"] == "alpha"
        assert data[0]["status"] == "mastered"
        db_path.unlink()


# ===================================================================
# 6. Filter learning
# ===================================================================

class TestFilterLearning:
    def test_filter_learning_returns_only_learning(self):
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "alpha", "seen_count": 10, "correct_count": 9},   # mastered
            {"word": "beta",  "seen_count": 10, "correct_count": 5},   # learning
            {"word": "gamma", "seen_count": 10, "correct_count": 1},   # weak
        ])
        resp = client.get("/api/vocabulary?filter=learning")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["word"] == "beta"
        assert data[0]["status"] == "learning"
        db_path.unlink()


# ===================================================================
# 7. Filter weak
# ===================================================================

class TestFilterWeak:
    def test_filter_weak_returns_only_weak(self):
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "alpha", "seen_count": 10, "correct_count": 9},   # mastered
            {"word": "beta",  "seen_count": 10, "correct_count": 5},   # learning
            {"word": "gamma", "seen_count": 10, "correct_count": 1},   # weak
        ])
        resp = client.get("/api/vocabulary?filter=weak")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["word"] == "gamma"
        assert data[0]["status"] == "weak"
        db_path.unlink()


# ===================================================================
# 8. Filter all
# ===================================================================

class TestFilterAll:
    def test_filter_all_returns_everything(self):
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "alpha", "seen_count": 10, "correct_count": 9},
            {"word": "beta",  "seen_count": 10, "correct_count": 5},
            {"word": "gamma", "seen_count": 10, "correct_count": 1},
        ])
        resp = client.get("/api/vocabulary?filter=all")
        data = resp.json()
        assert len(data) == 3
        words = {e["word"] for e in data}
        assert words == {"alpha", "beta", "gamma"}
        db_path.unlink()

    def test_default_filter_returns_everything(self):
        """No filter param should behave like filter=all."""
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "alpha", "seen_count": 10, "correct_count": 9},
            {"word": "beta",  "seen_count": 10, "correct_count": 5},
        ])
        resp = client.get("/api/vocabulary")
        assert len(resp.json()) == 2
        db_path.unlink()


# ===================================================================
# 9. Seen count increments on repeated submission
# ===================================================================

class TestSeenCountIncrements:
    def test_seen_count_increases_on_repeat(self):
        client, db_path = _fresh_authed_client()
        # Submit the same sentence twice
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})

        resp = client.get("/api/vocabulary")
        data = resp.json()
        for entry in data:
            assert entry["seen_count"] == 2, (
                f"Expected seen_count=2 for '{entry['word']}', got {entry['seen_count']}"
            )
        db_path.unlink()


# ===================================================================
# 10. Correct count increases only on correct dictation
# ===================================================================

class TestCorrectCount:
    def test_correct_count_increases_on_correct_submission(self):
        """Score >= 0.7 counts as correct, bumping correct_count."""
        client, db_path = _fresh_authed_client()
        # Perfect submission
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        resp = client.get("/api/vocabulary")
        data = resp.json()
        for entry in data:
            assert entry["correct_count"] == 1, (
                f"'{entry['word']}' correct_count should be 1, got {entry['correct_count']}"
            )
        db_path.unlink()

    def test_correct_count_unchanged_on_wrong_submission(self):
        """Score < 0.7 => correct_count should not increase."""
        client, db_path = _fresh_authed_client()
        # Totally wrong submission -> score ~ 0
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "xxxx yyyy zzzz wwww"})
        resp = client.get("/api/vocabulary")
        data = resp.json()
        for entry in data:
            assert entry["correct_count"] == 0, (
                f"'{entry['word']}' correct_count should be 0, got {entry['correct_count']}"
            )
        db_path.unlink()

    def test_mixed_correct_then_wrong(self):
        """One correct then one wrong: correct_count stays at 1, seen_count = 2."""
        client, db_path = _fresh_authed_client()
        # Correct
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        # Wrong
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "xxxx yyyy zzzz wwww"})
        resp = client.get("/api/vocabulary")
        data = resp.json()
        for entry in data:
            assert entry["seen_count"] == 2
            assert entry["correct_count"] == 1, (
                f"'{entry['word']}' correct_count should be 1, got {entry['correct_count']}"
            )
        db_path.unlink()


# ===================================================================
# 11. Flashcards endpoint returns cards ordered by weakness
# ===================================================================

class TestFlashcardsOrdering:
    def test_flashcards_ordered_weakest_first(self):
        client, db_path = _fresh_authed_client()
        _inject_vocab(db_path, 1, [
            {"word": "strong",  "ipa": "/s/", "pos": "adj", "seen_count": 10, "correct_count": 9},   # ratio 0.9
            {"word": "medium",  "ipa": "/m/", "pos": "adj", "seen_count": 10, "correct_count": 5},   # ratio 0.5
            {"word": "weakest", "ipa": "/w/", "pos": "adj", "seen_count": 10, "correct_count": 1},   # ratio 0.1
        ])
        resp = client.get("/api/vocabulary/flashcards")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Weakest ratio first
        assert data[0]["word"] == "weakest"
        assert data[1]["word"] == "medium"
        assert data[2]["word"] == "strong"
        db_path.unlink()


# ===================================================================
# 12. Flashcard fields present on each card
# ===================================================================

class TestFlashcardFields:
    def test_each_card_has_required_fields(self):
        client, db_path = _fresh_authed_client()
        # Practice sentence 1-01 so flashcards have data
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        resp = client.get("/api/vocabulary/flashcards")
        data = resp.json()
        required = {"word", "ipa", "pos", "example_sentence", "translation_zh", "translation_vi"}
        for card in data:
            assert required.issubset(card.keys()), (
                f"Missing fields: {required - card.keys()}"
            )
        db_path.unlink()


# ===================================================================
# 13. Flashcard ordering: weakest words come first
# ===================================================================

class TestFlashcardWeaknessOrdering:
    def test_weakness_ordering_after_practice(self):
        """Practice two sentences: one correct, one wrong.
        Words from the wrong submission should appear before correct ones."""
        client, db_path = _fresh_authed_client()
        # Correct submission for sentence 1-01
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        # Wrong submission for sentence 1-06 ("Good morning!")
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-06", "typed_text": "xxxx yyyy"})

        resp = client.get("/api/vocabulary/flashcards")
        data = resp.json()
        assert len(data) > 0

        # Words from sentence 1-06 (wrong) have ratio 0/1 = 0
        # Words from sentence 1-01 (correct) have ratio 1/1 = 1
        # So the first cards should be the weak ones
        weak_words = {"good", "morning"}
        # Find positions of weak words; they should be at the front
        for i, card in enumerate(data):
            if card["word"] in weak_words:
                # Should be in the first portion of results
                assert i < len(weak_words) + 2, (
                    f"Weak word '{card['word']}' at position {i}, expected near the front"
                )
        db_path.unlink()


# ===================================================================
# 14. Flashcards limit: max 20 cards
# ===================================================================

class TestFlashcardsLimit:
    def test_max_20_flashcards_returned(self):
        client, db_path = _fresh_authed_client()
        # Inject 30 vocabulary entries
        entries = [
            {"word": f"word{i:03d}", "ipa": f"/w{i}/", "pos": "noun",
             "seen_count": 5, "correct_count": i % 5}
            for i in range(30)
        ]
        _inject_vocab(db_path, 1, entries)
        resp = client.get("/api/vocabulary/flashcards")
        data = resp.json()
        assert len(data) <= 20, f"Expected max 20 flashcards, got {len(data)}"
        db_path.unlink()


# ===================================================================
# 15. Empty flashcards for new user with no vocabulary
# ===================================================================

class TestEmptyFlashcards:
    def test_new_user_gets_empty_flashcard_list(self):
        client, db_path = _fresh_authed_client()
        resp = client.get("/api/vocabulary/flashcards")
        assert resp.status_code == 200
        assert resp.json() == []
        db_path.unlink()


# ===================================================================
# 16. Auth required: vocabulary endpoints without login return 401
# ===================================================================

class TestAuthRequired:
    def test_vocabulary_requires_auth(self):
        client, db_path = _make_app_seeded()
        resp = client.get("/api/vocabulary")
        assert resp.status_code == 401
        db_path.unlink()

    def test_flashcards_requires_auth(self):
        client, db_path = _make_app_seeded()
        resp = client.get("/api/vocabulary/flashcards")
        assert resp.status_code == 401
        db_path.unlink()

    def test_vocabulary_filter_requires_auth(self):
        client, db_path = _make_app_seeded()
        resp = client.get("/api/vocabulary?filter=mastered")
        assert resp.status_code == 401
        db_path.unlink()


# ===================================================================
# 17. Multiple users have independent vocabulary lists
# ===================================================================

class TestMultipleUsersIndependence:
    def test_two_users_have_separate_vocab(self):
        """Alice practices lesson 1 sentence 1, Bob practices lesson 2 sentence 1.
        Their vocabulary lists must not overlap."""
        client, db_path = _make_app_seeded()

        # --- Alice ---
        _register_and_login(client, "alice", "pass1")
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        alice_vocab = client.get("/api/vocabulary").json()
        alice_words = {e["word"] for e in alice_vocab}
        client.post("/api/auth/logout")

        # --- Bob ---
        _register_and_login(client, "bob", "pass2")
        client.post("/api/practice/submit",
                     json={"sentence_id": "2-01",
                           "typed_text": "I wake up at seven o'clock."})
        bob_vocab = client.get("/api/vocabulary").json()
        bob_words = {e["word"] for e in bob_vocab}
        client.post("/api/auth/logout")

        # Alice should have lesson-1 words, not lesson-2 words
        assert "gorgeous" in alice_words
        assert "wake" not in alice_words

        # Bob should have lesson-2 words, not lesson-1 exclusive words
        assert "wake" in bob_words
        assert "gorgeous" not in bob_words
        db_path.unlink()

    def test_shared_words_tracked_independently(self):
        """Both users practice sentences containing common words.
        Counts should be independent."""
        client, db_path = _make_app_seeded()

        # Sentence 1-01 has "you"; sentence 1-03 also has "you"
        # Alice practices 1-01 correctly
        _register_and_login(client, "alice", "pass1")
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        alice_vocab = {e["word"]: e for e in client.get("/api/vocabulary").json()}
        client.post("/api/auth/logout")

        # Bob practices 1-01 incorrectly, then again correctly (2 seen, 1 correct)
        _register_and_login(client, "bob", "pass2")
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "xxxx yyyy zzzz wwww"})
        client.post("/api/practice/submit",
                     json={"sentence_id": "1-01", "typed_text": "Hi Min, you look gorgeous."})
        bob_vocab = {e["word"]: e for e in client.get("/api/vocabulary").json()}
        client.post("/api/auth/logout")

        # Alice: seen=1, correct=1
        assert alice_vocab["you"]["seen_count"] == 1
        assert alice_vocab["you"]["correct_count"] == 1

        # Bob: seen=2, correct=1
        assert bob_vocab["you"]["seen_count"] == 2
        assert bob_vocab["you"]["correct_count"] == 1

        db_path.unlink()
