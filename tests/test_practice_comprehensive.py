"""
Comprehensive tests for dictation, scoring, and practice flows.

Covers:
  1. Perfect dictation
  2. Case insensitive scoring
  3. Punctuation ignored
  4. One typo (close match)
  5. Missing word
  6. Extra word
  7. Completely wrong text
  8. Empty submission
  9. XP thresholds
 10. XP accumulation
 11. Streak tracking
 12. Self-rate (good)
 13. Self-rate (okay)
 14. Self-rate (again)
 15. Progress tracking (total_sentences_practiced)
 16. Sentences today
 17. Spaced repetition / Leitner bucket changes
 18. Non-existent sentence -> 404
 19. Auth required -> 401
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import create_app
from app.routers.auth import SESSIONS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_words(word_list):
    """Build a minimal words_json list from a list of word strings."""
    return [
        {
            "word": w,
            "ipa": f"/{w}/",
            "pos": "noun",
            "pos_zh": "名词",
            "pos_vi": "danh tu",
            "role": "subject",
            "role_zh": "主语",
            "role_vi": "chu ngu",
            "group": 0,
            "group_color": "#2196F3",
        }
        for w in word_list
    ]


def _make_constituents():
    return [
        {
            "group": 0,
            "label_en": "clause",
            "label_zh": "子句",
            "label_vi": "menh de",
            "word_indices": [0],
            "color": "#2196F3",
        }
    ]


def _seed(db_path: Path):
    """Insert two lessons with several sentences of varying complexity."""
    conn = sqlite3.connect(str(db_path))

    # Lesson 1 – Greetings
    conn.execute(
        "INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "Greetings", "问候", "Chao hoi", "A1", "daily_conversation", 5),
    )

    sentences = [
        ("1-01", 1, 1, "Hello, how are you?"),
        ("1-02", 1, 2, "I am fine, thank you."),
        ("1-03", 1, 3, "Nice to meet you."),
        ("1-04", 1, 4, "What is your name?"),
        ("1-05", 1, 5, "My name is David."),
    ]

    for sid, lid, idx, text in sentences:
        words = _make_words(text.replace(",", "").replace(".", "").replace("?", "").replace("!", "").split())
        conn.execute(
            "INSERT INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, lid, idx, text, "翻译", "Dich", json.dumps(words), json.dumps(_make_constituents())),
        )

    # Lesson 2 – Weather
    conn.execute(
        "INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)",
        (2, "Weather", "天气", "Thoi tiet", "A2", "daily_conversation", 2),
    )
    for sid, lid, idx, text in [
        ("2-01", 2, 1, "It is raining outside."),
        ("2-02", 2, 2, "The weather is beautiful today."),
    ]:
        words = _make_words(text.replace(",", "").replace(".", "").split())
        conn.execute(
            "INSERT INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, lid, idx, text, "翻译", "Dich", json.dumps(words), json.dumps(_make_constituents())),
        )

    conn.commit()
    conn.close()


@pytest.fixture()
def env():
    """Yield (client, db_path) with a seeded in-memory-like temp DB.

    The SESSIONS dict is cleared between tests so logins don't leak.
    """
    SESSIONS.clear()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    init_db(db_path)
    _seed(db_path)
    app = create_app(db_path)
    client = TestClient(app)
    yield client, db_path
    db_path.unlink(missing_ok=True)


def _register_and_login(client: TestClient, username="alice", password="pass123"):
    """Register + login, return client (cookies are stored on the TestClient)."""
    client.post("/api/auth/register", json={"username": username, "password": password})
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return client


# ---------------------------------------------------------------------------
# 1. Perfect dictation
# ---------------------------------------------------------------------------

class TestPerfectDictation:
    def test_exact_text_gives_perfect_score(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "Hello how are you"},
        )
        data = resp.json()
        assert resp.status_code == 200
        assert data["score"] == 1.0
        assert data["xp_earned"] == 10
        assert all(d["status"] == "correct" for d in data["diffs"])


# ---------------------------------------------------------------------------
# 2. Case insensitive
# ---------------------------------------------------------------------------

class TestCaseInsensitive:
    def test_lowercase_still_perfect(self, env):
        client, _ = env
        _register_and_login(client)
        # Original text: "Hello, how are you?" – submit all-lowercase, no punctuation
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        data = resp.json()
        assert data["score"] == 1.0

    def test_uppercase_still_perfect(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "HELLO HOW ARE YOU"},
        )
        data = resp.json()
        assert data["score"] == 1.0


# ---------------------------------------------------------------------------
# 3. Punctuation ignored
# ---------------------------------------------------------------------------

class TestPunctuationIgnored:
    def test_without_punctuation_perfect(self, env):
        client, _ = env
        _register_and_login(client)
        # Original: "I am fine, thank you."
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "i am fine thank you"},
        )
        data = resp.json()
        assert data["score"] == 1.0

    def test_with_extra_punctuation_still_perfect(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "I am fine!!! thank you..."},
        )
        data = resp.json()
        assert data["score"] == 1.0


# ---------------------------------------------------------------------------
# 4. One typo (close match, Levenshtein <= 2)
# ---------------------------------------------------------------------------

class TestOneTypo:
    def test_close_match_detected(self, env):
        client, _ = env
        _register_and_login(client)
        # "Hello, how are you?" -> submit "helo how are you" (helo: lev distance 1)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "helo how are you"},
        )
        data = resp.json()
        assert data["score"] > 0.8
        close = [d for d in data["diffs"] if d["status"] == "close"]
        assert len(close) >= 1
        assert close[0]["word"] == "helo"
        assert close[0]["expected"] == "hello"

    def test_two_char_typo_still_close(self, env):
        client, _ = env
        _register_and_login(client)
        # "name" -> "namm" is lev distance 1; "David" -> "Dvid" lev 1
        # Original: "My name is David."
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-05", "typed_text": "my namm is dvid"},
        )
        data = resp.json()
        close = [d for d in data["diffs"] if d["status"] == "close"]
        assert len(close) >= 1


# ---------------------------------------------------------------------------
# 5. Missing word
# ---------------------------------------------------------------------------

class TestMissingWord:
    def test_missing_last_word(self, env):
        client, _ = env
        _register_and_login(client)
        # Original: "Hello, how are you?" -> omit "you"
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are"},
        )
        data = resp.json()
        assert data["score"] < 1.0
        missing = [d for d in data["diffs"] if d["status"] == "missing"]
        assert len(missing) >= 1
        assert any(m["word"] == "you" for m in missing)

    def test_missing_middle_word(self, env):
        client, _ = env
        _register_and_login(client)
        # Original: "Nice to meet you." -> omit "to"
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-03", "typed_text": "nice meet you"},
        )
        data = resp.json()
        assert data["score"] < 1.0
        missing = [d for d in data["diffs"] if d["status"] == "missing"]
        assert len(missing) >= 1


# ---------------------------------------------------------------------------
# 6. Extra word
# ---------------------------------------------------------------------------

class TestExtraWord:
    def test_extra_word_at_end(self, env):
        client, _ = env
        _register_and_login(client)
        # Original: "Hello, how are you?" -> add "today"
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you today"},
        )
        data = resp.json()
        extra = [d for d in data["diffs"] if d["status"] == "extra"]
        assert len(extra) >= 1
        assert any(e["word"] == "today" for e in extra)

    def test_extra_word_in_middle(self, env):
        client, _ = env
        _register_and_login(client)
        # Original: "Nice to meet you." -> "nice to really meet you"
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-03", "typed_text": "nice to really meet you"},
        )
        data = resp.json()
        extra = [d for d in data["diffs"] if d["status"] == "extra"]
        assert len(extra) >= 1


# ---------------------------------------------------------------------------
# 7. Completely wrong
# ---------------------------------------------------------------------------

class TestCompletelyWrong:
    def test_totally_different_text(self, env):
        client, _ = env
        _register_and_login(client)
        # Original: "Hello, how are you?"
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "elephant tornado pizza submarine"},
        )
        data = resp.json()
        assert data["score"] == 0.0
        assert data["xp_earned"] == 0


# ---------------------------------------------------------------------------
# 8. Empty submission
# ---------------------------------------------------------------------------

class TestEmptySubmission:
    def test_empty_string(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": ""},
        )
        data = resp.json()
        assert data["score"] == 0.0
        assert data["xp_earned"] == 0

    def test_whitespace_only(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "   "},
        )
        data = resp.json()
        assert data["score"] == 0.0
        assert data["xp_earned"] == 0


# ---------------------------------------------------------------------------
# 9. XP thresholds
# ---------------------------------------------------------------------------

class TestXPThresholds:
    def test_perfect_score_10_xp(self, env):
        """score >= 0.95 => 10 XP"""
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        data = resp.json()
        assert data["score"] >= 0.95
        assert data["xp_earned"] == 10

    def test_close_score_5_xp(self, env):
        """score >= 0.7 but < 0.95 => 5 XP"""
        client, _ = env
        _register_and_login(client)
        # Original: "I am fine, thank you." (5 words)
        # Submit with one typo: "i am fne thank you" -> 4 correct + 1 close
        # score = (4 + 0.8) / 5 = 0.96 – that's too high.
        # Let's use: "i am fne thnk you" -> 3 correct + 2 close
        # score = (3 + 2*0.8) / 5 = (3 + 1.6)/5 = 0.92 => xp=5
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "i am fne thnk you"},
        )
        data = resp.json()
        assert 0.7 <= data["score"] < 0.95
        assert data["xp_earned"] == 5

    def test_bad_score_0_xp(self, env):
        """score < 0.7 => 0 XP"""
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "elephant tornado pizza submarine"},
        )
        data = resp.json()
        assert data["score"] < 0.7
        assert data["xp_earned"] == 0


# ---------------------------------------------------------------------------
# 10. XP accumulation
# ---------------------------------------------------------------------------

class TestXPAccumulation:
    def test_xp_increases_across_submissions(self, env):
        client, _ = env
        _register_and_login(client)

        # First submission – perfect
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        xp1 = resp.json()["xp_earned"]

        stats1 = client.get("/api/stats").json()
        assert stats1["xp"] == xp1

        # Second submission – perfect on different sentence
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "i am fine thank you"},
        )
        xp2 = resp.json()["xp_earned"]

        stats2 = client.get("/api/stats").json()
        assert stats2["xp"] == xp1 + xp2

    def test_xp_zero_does_not_decrease(self, env):
        client, _ = env
        _register_and_login(client)

        # Perfect first
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        stats_before = client.get("/api/stats").json()

        # Terrible second
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "xyz xyz xyz xyz xyz"},
        )
        stats_after = client.get("/api/stats").json()
        assert stats_after["xp"] >= stats_before["xp"]


# ---------------------------------------------------------------------------
# 11. Streak tracking
# ---------------------------------------------------------------------------

class TestStreakTracking:
    def test_first_practice_sets_streak_to_1(self, env):
        client, _ = env
        _register_and_login(client)

        stats_before = client.get("/api/stats").json()
        assert stats_before["streak_days"] == 0

        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )

        stats_after = client.get("/api/stats").json()
        assert stats_after["streak_days"] == 1

    def test_same_day_keeps_streak(self, env):
        client, _ = env
        _register_and_login(client)

        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "i am fine thank you"},
        )
        stats = client.get("/api/stats").json()
        assert stats["streak_days"] == 1


# ---------------------------------------------------------------------------
# 12. Self-rate (good)
# ---------------------------------------------------------------------------

class TestSelfRateGood:
    def test_good_rating_returns_ok(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-01", "rating": "good"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == "good"
        assert data["message"] == "Rated"


# ---------------------------------------------------------------------------
# 13. Self-rate (okay)
# ---------------------------------------------------------------------------

class TestSelfRateOkay:
    def test_okay_rating_returns_ok(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-01", "rating": "okay"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == "okay"


# ---------------------------------------------------------------------------
# 14. Self-rate (again)
# ---------------------------------------------------------------------------

class TestSelfRateAgain:
    def test_again_rating_returns_ok(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-01", "rating": "again"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == "again"


# ---------------------------------------------------------------------------
# 15. Progress tracking (total_sentences_practiced)
# ---------------------------------------------------------------------------

class TestProgressTracking:
    def test_count_increases_with_unique_sentences(self, env):
        client, _ = env
        _register_and_login(client)

        stats0 = client.get("/api/stats").json()
        assert stats0["total_sentences_practiced"] == 0

        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        stats1 = client.get("/api/stats").json()
        assert stats1["total_sentences_practiced"] == 1

        # Same sentence again – should still be counted as 1 unique
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        stats1b = client.get("/api/stats").json()
        assert stats1b["total_sentences_practiced"] == 1

        # Different sentence
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "i am fine thank you"},
        )
        stats2 = client.get("/api/stats").json()
        assert stats2["total_sentences_practiced"] == 2

    def test_self_rate_also_counted_as_practiced(self, env):
        """Self-rate creates progress rows too, so it adds to the count."""
        client, _ = env
        _register_and_login(client)

        client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-03", "rating": "good"},
        )
        stats = client.get("/api/stats").json()
        assert stats["total_sentences_practiced"] >= 1


# ---------------------------------------------------------------------------
# 16. Sentences today
# ---------------------------------------------------------------------------

class TestSentencesToday:
    def test_sentences_today_increments(self, env):
        client, _ = env
        _register_and_login(client)

        stats0 = client.get("/api/stats").json()
        assert stats0["sentences_today"] == 0

        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        stats1 = client.get("/api/stats").json()
        assert stats1["sentences_today"] == 1

        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "i am fine thank you"},
        )
        stats2 = client.get("/api/stats").json()
        assert stats2["sentences_today"] == 2

    def test_same_sentence_not_double_counted_today(self, env):
        client, _ = env
        _register_and_login(client)

        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        stats = client.get("/api/stats").json()
        assert stats["sentences_today"] == 1


# ---------------------------------------------------------------------------
# 17. Spaced repetition / Leitner bucket changes
# ---------------------------------------------------------------------------

class TestSpacedRepetition:
    def test_correct_answer_promotes_bucket(self, env):
        client, db_path = env
        _register_and_login(client)

        # First correct submission -> bucket starts at 1, correct => new_bucket = 2
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )

        due = client.get("/api/review/due").json()
        entry = [r for r in due if r["sentence_id"] == "1-01"]
        # It was just submitted, so it is scheduled for future review.
        # Check the bucket via direct DB query.
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT leitner_bucket FROM user_progress WHERE sentence_id = '1-01' AND mode = 'dictation'"
        ).fetchone()
        conn.close()
        assert row["leitner_bucket"] == 2  # promoted from initial 1

    def test_incorrect_answer_resets_bucket(self, env):
        client, db_path = env
        _register_and_login(client)

        # First correct to get to bucket 2
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello how are you"},
        )
        # Second incorrect (score < 0.7) to reset to bucket 1
        client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "elephant tornado pizza submarine"},
        )

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT leitner_bucket FROM user_progress WHERE sentence_id = '1-01' AND mode = 'dictation'"
        ).fetchone()
        conn.close()
        assert row["leitner_bucket"] == 1  # reset

    def test_self_rate_good_promotes_bucket(self, env):
        client, db_path = env
        _register_and_login(client)

        client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-01", "rating": "good"},
        )
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT leitner_bucket FROM user_progress WHERE sentence_id = '1-01' AND mode = 'read_aloud'"
        ).fetchone()
        conn.close()
        assert row["leitner_bucket"] == 2

    def test_self_rate_again_resets_bucket(self, env):
        client, db_path = env
        _register_and_login(client)

        # First promote
        client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-01", "rating": "good"},
        )
        # Then demote
        client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-01", "rating": "again"},
        )
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT leitner_bucket FROM user_progress WHERE sentence_id = '1-01' AND mode = 'read_aloud'"
        ).fetchone()
        conn.close()
        assert row["leitner_bucket"] == 1

    def test_multiple_corrects_promote_to_higher_buckets(self, env):
        """Simulate rapid correct submissions to push bucket from 1 -> 2 -> 3."""
        client, db_path = env
        _register_and_login(client)

        # Correct submissions
        for _ in range(2):
            client.post(
                "/api/practice/submit",
                json={"sentence_id": "1-04", "typed_text": "what is your name"},
            )

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT leitner_bucket FROM user_progress WHERE sentence_id = '1-04' AND mode = 'dictation'"
        ).fetchone()
        conn.close()
        assert row["leitner_bucket"] == 3  # 1 -> 2 -> 3


# ---------------------------------------------------------------------------
# 18. Non-existent sentence -> 404
# ---------------------------------------------------------------------------

class TestNonExistentSentence:
    def test_submit_invalid_sentence_404(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "999-99", "typed_text": "anything"},
        )
        assert resp.status_code == 404

    def test_self_rate_invalid_sentence_404(self, env):
        client, _ = env
        _register_and_login(client)
        resp = client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "999-99", "rating": "good"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 19. Auth required -> 401
# ---------------------------------------------------------------------------

class TestAuthRequired:
    def test_submit_without_login_401(self, env):
        client, _ = env
        # No login
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "hello"},
        )
        assert resp.status_code == 401

    def test_self_rate_without_login_401(self, env):
        client, _ = env
        resp = client.post(
            "/api/practice/self-rate",
            json={"sentence_id": "1-01", "rating": "good"},
        )
        assert resp.status_code == 401

    def test_stats_without_login_401(self, env):
        client, _ = env
        resp = client.get("/api/stats")
        assert resp.status_code == 401

    def test_review_due_without_login_401(self, env):
        client, _ = env
        resp = client.get("/api/review/due")
        assert resp.status_code == 401
