"""Comprehensive tests for lesson and sentence API flows.

Covers:
1.  List lessons (all 3 seeded)
2.  Lesson detail with full sentences array
3.  Sentence detail with all annotations
4.  Word annotation completeness
5.  Constituent annotation completeness
6.  Vietnamese translations present
7.  Chinese translations contain CJK characters
8.  IPA format /.../ validation
9.  POS-based group_color mapping
10. Invalid lesson -> 404
11. Invalid sentence -> 404
12. Completed count increments after practice
13. Auth-required endpoints return 401
"""

import json
import re
import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.database import init_db

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(
    "/fsx-neo/dedicated-fsx-data-repo-neo-us-east-1/toyng/toyng_ws/"
    "projects/Personalized_Product_search/englisht_turorial/data/lessons"
)

# Expected POS -> group_color mapping from the lesson data
POS_COLOR_MAP = {
    "noun": "#2196F3",
    "verb": "#F44336",
    "adjective": "#FF9800",
    "adverb": "#4CAF50",
    "pronoun": "#9C27B0",
    "determiner": "#3F51B5",
    "preposition": "#607D8B",
    "particle": "#00BCD4",
    "interjection": "#795548",
}

# We seed three lessons (lesson_001, lesson_002, lesson_003)
LESSON_FILES = ["lesson_001.json", "lesson_002.json", "lesson_003.json"]

# CJK Unicode range check
CJK_RE = re.compile(r"[一-鿿]")

# IPA regex: must start and end with /
IPA_RE = re.compile(r"^/.+/$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_lesson_json(filename: str) -> dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def _create_test_app() -> tuple[TestClient, Path]:
    """Create a fresh app with a temp DB."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(tmp.name)
    tmp.close()
    init_db(db_path)
    app = create_app(db_path)
    client = TestClient(app)
    return client, db_path


def _seed_all_lessons(db_path: Path):
    """Load the 3 lesson JSON files and insert into the test DB."""
    conn = sqlite3.connect(str(db_path))
    for filename in LESSON_FILES:
        lesson = _load_lesson_json(filename)
        conn.execute(
            "INSERT OR IGNORE INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                lesson["id"],
                lesson["title"],
                lesson["title_zh"],
                lesson["title_vi"],
                lesson["difficulty"],
                lesson["category"],
                len(lesson["sentences"]),
            ),
        )
        for s in lesson["sentences"]:
            sid = f"{lesson['id']}-{s['index']:02d}"
            conn.execute(
                "INSERT OR IGNORE INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sid,
                    lesson["id"],
                    s["index"],
                    s["text"],
                    s["translation_zh"],
                    s["translation_vi"],
                    json.dumps(s["words"]),
                    json.dumps(s["constituents"]),
                ),
            )
    conn.commit()
    conn.close()


def _register_and_login(client: TestClient, username: str = "testuser"):
    """Register + login, returning the client (cookies set automatically)."""
    client.post("/api/auth/register", json={"username": username, "password": "pass123"})
    client.post("/api/auth/login", json={"username": username, "password": "pass123"})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def setup():
    """Yield (client, db_path) with seeded lessons and an authenticated user."""
    client, db_path = _create_test_app()
    _seed_all_lessons(db_path)
    _register_and_login(client)
    yield client, db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture()
def unauthenticated_setup():
    """Yield (client, db_path) with seeded lessons but NO logged-in user."""
    client, db_path = _create_test_app()
    _seed_all_lessons(db_path)
    yield client, db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture()
def lesson_data():
    """Return the raw JSON dicts for the 3 seeded lessons."""
    return [_load_lesson_json(f) for f in LESSON_FILES]


# ===================================================================
# 1. List lessons: returns all 3 lessons with correct fields
# ===================================================================
class TestListLessons:
    def test_returns_all_three_lessons(self, setup, lesson_data):
        client, _ = setup
        resp = client.get("/api/lessons")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3, f"Expected 3 lessons, got {len(data)}"

    def test_lesson_ids_match(self, setup, lesson_data):
        client, _ = setup
        data = client.get("/api/lessons").json()
        ids = {l["id"] for l in data}
        expected_ids = {ld["id"] for ld in lesson_data}
        assert ids == expected_ids

    def test_lesson_summary_has_all_fields(self, setup):
        client, _ = setup
        data = client.get("/api/lessons").json()
        required = {"id", "title", "title_zh", "title_vi", "difficulty", "category",
                     "sentence_count", "completed_count"}
        for lesson in data:
            missing = required - set(lesson.keys())
            assert not missing, f"Lesson {lesson.get('id')} missing fields: {missing}"

    def test_sentence_counts_match_json(self, setup, lesson_data):
        client, _ = setup
        data = client.get("/api/lessons").json()
        by_id = {l["id"]: l for l in data}
        for ld in lesson_data:
            assert by_id[ld["id"]]["sentence_count"] == len(ld["sentences"]), \
                f"Lesson {ld['id']} sentence_count mismatch"

    def test_titles_non_empty(self, setup):
        client, _ = setup
        for lesson in client.get("/api/lessons").json():
            assert lesson["title"], f"Lesson {lesson['id']} has empty title"
            assert lesson["title_zh"], f"Lesson {lesson['id']} has empty title_zh"
            assert lesson["title_vi"], f"Lesson {lesson['id']} has empty title_vi"


# ===================================================================
# 2. Lesson detail: GET /api/lessons/{id}
# ===================================================================
class TestLessonDetail:
    def test_lesson_1_returns_full_detail(self, setup, lesson_data):
        client, _ = setup
        resp = client.get("/api/lessons/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        assert "sentences" in data
        assert isinstance(data["sentences"], list)

    def test_sentences_array_length(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            assert len(data["sentences"]) == len(ld["sentences"]), \
                f"Lesson {ld['id']} sentences count mismatch"

    def test_sentence_fields_present(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        required = {"id", "index", "text", "translation_zh", "translation_vi",
                     "words", "constituents"}
        for s in data["sentences"]:
            missing = required - set(s.keys())
            assert not missing, f"Sentence {s.get('id')} missing: {missing}"

    def test_sentence_words_is_list(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        for s in data["sentences"]:
            assert isinstance(s["words"], list), f"Sentence {s['id']} words not list"
            assert len(s["words"]) > 0, f"Sentence {s['id']} has 0 words"

    def test_sentence_constituents_is_list(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        for s in data["sentences"]:
            assert isinstance(s["constituents"], list)
            assert len(s["constituents"]) > 0


# ===================================================================
# 3. Sentence detail: GET /api/lessons/{id}/sentences/{idx}
# ===================================================================
class TestSentenceDetail:
    def test_get_sentence_1_of_lesson_1(self, setup):
        client, _ = setup
        resp = client.get("/api/lessons/1/sentences/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["index"] == 1
        assert data["lesson_id"] == 1

    def test_sentence_has_all_annotation_fields(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1/sentences/1").json()
        required = {"id", "lesson_id", "index", "text", "translation_zh",
                     "translation_vi", "words", "constituents"}
        missing = required - set(data.keys())
        assert not missing, f"Sentence detail missing fields: {missing}"

    def test_sentence_text_matches_source(self, setup, lesson_data):
        client, _ = setup
        ld = lesson_data[0]  # lesson 1
        for s in ld["sentences"]:
            data = client.get(f"/api/lessons/1/sentences/{s['index']}").json()
            assert data["text"] == s["text"], \
                f"Sentence {s['index']} text mismatch"

    def test_all_sentences_across_all_lessons(self, setup, lesson_data):
        """Verify every sentence in every lesson is retrievable."""
        client, _ = setup
        for ld in lesson_data:
            for s in ld["sentences"]:
                resp = client.get(f"/api/lessons/{ld['id']}/sentences/{s['index']}")
                assert resp.status_code == 200, \
                    f"Failed to get lesson {ld['id']} sentence {s['index']}"


# ===================================================================
# 4. Word annotations: every word has required fields
# ===================================================================
class TestWordAnnotations:
    WORD_FIELDS = {"word", "ipa", "pos", "pos_zh", "pos_vi", "role", "role_zh",
                   "role_vi", "group", "group_color"}

    def test_all_word_fields_present(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for i, w in enumerate(s["words"]):
                    missing = self.WORD_FIELDS - set(w.keys())
                    assert not missing, \
                        f"Lesson {ld['id']} sentence {s['index']} word {i} missing: {missing}"

    def test_word_field_types(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        for s in data["sentences"]:
            for w in s["words"]:
                assert isinstance(w["word"], str) and w["word"]
                assert isinstance(w["ipa"], str) and w["ipa"]
                assert isinstance(w["pos"], str) and w["pos"]
                assert isinstance(w["group"], int)
                assert isinstance(w["group_color"], str) and w["group_color"].startswith("#")

    def test_ipa_starts_with_slash(self, setup, lesson_data):
        """Every IPA must begin with /."""
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for w in s["words"]:
                    assert w["ipa"].startswith("/"), \
                        f"IPA '{w['ipa']}' for word '{w['word']}' does not start with /"


# ===================================================================
# 5. Constituent annotations: each has required fields with valid indices
# ===================================================================
class TestConstituentAnnotations:
    CONSTITUENT_FIELDS = {"group", "label_en", "label_zh", "label_vi",
                          "word_indices", "color"}

    def test_all_constituent_fields_present(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for c in s["constituents"]:
                    missing = self.CONSTITUENT_FIELDS - set(c.keys())
                    assert not missing, \
                        f"Lesson {ld['id']} sentence {s['index']} constituent missing: {missing}"

    def test_word_indices_valid(self, setup, lesson_data):
        """word_indices must contain valid indices into the words array."""
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                num_words = len(s["words"])
                for c in s["constituents"]:
                    for idx in c["word_indices"]:
                        assert 0 <= idx < num_words, \
                            f"Invalid word_index {idx} (num_words={num_words}) " \
                            f"in lesson {ld['id']} sentence {s['index']}"

    def test_constituent_color_format(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for c in s["constituents"]:
                    assert c["color"].startswith("#"), \
                        f"Bad color '{c['color']}' in lesson {ld['id']} sentence {s['index']}"
                    assert len(c["color"]) == 7, \
                        f"Color '{c['color']}' not a 7-char hex code"

    def test_constituent_labels_non_empty(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for c in s["constituents"]:
                    assert c["label_en"], "label_en is empty"
                    assert c["label_zh"], "label_zh is empty"
                    assert c["label_vi"], "label_vi is empty"


# ===================================================================
# 6. Vietnamese translations: present and non-empty
# ===================================================================
class TestVietnameseTranslations:
    def test_all_sentences_have_translation_vi(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                assert s["translation_vi"], \
                    f"Lesson {ld['id']} sentence {s['index']} missing translation_vi"

    def test_translation_vi_is_string(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                assert isinstance(s["translation_vi"], str)

    def test_translation_vi_via_sentence_detail(self, setup, lesson_data):
        """Verify via the /sentences/{idx} endpoint too."""
        client, _ = setup
        for ld in lesson_data:
            for src_s in ld["sentences"]:
                data = client.get(
                    f"/api/lessons/{ld['id']}/sentences/{src_s['index']}"
                ).json()
                assert data["translation_vi"], \
                    f"Sentence detail missing translation_vi"


# ===================================================================
# 7. Chinese translations: contain actual CJK characters
# ===================================================================
class TestChineseTranslations:
    def test_all_sentences_have_translation_zh(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                assert s["translation_zh"], \
                    f"Lesson {ld['id']} sentence {s['index']} missing translation_zh"

    def test_translation_zh_contains_chinese_chars(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                assert CJK_RE.search(s["translation_zh"]), \
                    f"translation_zh '{s['translation_zh']}' in lesson {ld['id']} " \
                    f"sentence {s['index']} has no CJK characters"

    def test_translation_zh_via_sentence_detail(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            for src_s in ld["sentences"]:
                data = client.get(
                    f"/api/lessons/{ld['id']}/sentences/{src_s['index']}"
                ).json()
                assert CJK_RE.search(data["translation_zh"]), \
                    f"Sentence detail translation_zh lacks CJK chars"


# ===================================================================
# 8. IPA format: every IPA starts with / and ends with /
# ===================================================================
class TestIPAFormat:
    def test_ipa_slash_delimited(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for w in s["words"]:
                    assert IPA_RE.match(w["ipa"]), \
                        f"IPA '{w['ipa']}' for '{w['word']}' in lesson {ld['id']} " \
                        f"sentence {s['index']} not /.../ format"

    def test_ipa_via_sentence_detail(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1/sentences/1").json()
        for w in data["words"]:
            assert w["ipa"].startswith("/") and w["ipa"].endswith("/"), \
                f"IPA '{w['ipa']}' not slash-delimited"


# ===================================================================
# 9. POS colors: verify group_color matches expected POS color mapping
# ===================================================================
class TestPOSColors:
    def test_known_pos_colors(self, setup, lesson_data):
        """For every word whose POS is in our known mapping, verify group_color."""
        client, _ = setup
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for w in s["words"]:
                    pos = w["pos"]
                    if pos in POS_COLOR_MAP:
                        expected = POS_COLOR_MAP[pos]
                        assert w["group_color"] == expected, \
                            f"Word '{w['word']}' (pos={pos}) in lesson {ld['id']} " \
                            f"sentence {s['index']}: expected color {expected}, " \
                            f"got {w['group_color']}"

    def test_group_color_is_hex(self, setup, lesson_data):
        client, _ = setup
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for ld in lesson_data:
            data = client.get(f"/api/lessons/{ld['id']}").json()
            for s in data["sentences"]:
                for w in s["words"]:
                    assert hex_re.match(w["group_color"]), \
                        f"group_color '{w['group_color']}' not valid hex"

    def test_noun_is_blue(self, setup):
        """Spot-check: any noun word should be #2196F3."""
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        for s in data["sentences"]:
            for w in s["words"]:
                if w["pos"] == "noun":
                    assert w["group_color"] == "#2196F3"

    def test_verb_is_red(self, setup):
        """Spot-check: any verb word should be #F44336."""
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        for s in data["sentences"]:
            for w in s["words"]:
                if w["pos"] == "verb":
                    assert w["group_color"] == "#F44336"

    def test_adjective_is_orange(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        for s in data["sentences"]:
            for w in s["words"]:
                if w["pos"] == "adjective":
                    assert w["group_color"] == "#FF9800"

    def test_pronoun_is_purple(self, setup):
        client, _ = setup
        data = client.get("/api/lessons/1").json()
        for s in data["sentences"]:
            for w in s["words"]:
                if w["pos"] == "pronoun":
                    assert w["group_color"] == "#9C27B0"


# ===================================================================
# 10. Invalid lesson: GET /api/lessons/999 -> 404
# ===================================================================
class TestInvalidLesson:
    def test_nonexistent_lesson_returns_404(self, setup):
        client, _ = setup
        resp = client.get("/api/lessons/999")
        assert resp.status_code == 404

    def test_lesson_zero_returns_404(self, setup):
        client, _ = setup
        resp = client.get("/api/lessons/0")
        assert resp.status_code == 404

    def test_negative_lesson_returns_404(self, setup):
        client, _ = setup
        resp = client.get("/api/lessons/-1")
        assert resp.status_code == 404


# ===================================================================
# 11. Invalid sentence: GET /api/lessons/1/sentences/99 -> 404
# ===================================================================
class TestInvalidSentence:
    def test_nonexistent_sentence_returns_404(self, setup):
        client, _ = setup
        resp = client.get("/api/lessons/1/sentences/99")
        assert resp.status_code == 404

    def test_sentence_zero_returns_404(self, setup):
        client, _ = setup
        resp = client.get("/api/lessons/1/sentences/0")
        assert resp.status_code == 404

    def test_sentence_in_nonexistent_lesson(self, setup):
        client, _ = setup
        resp = client.get("/api/lessons/999/sentences/1")
        assert resp.status_code == 404


# ===================================================================
# 12. Completed count: starts at 0, increments after practice
# ===================================================================
class TestCompletedCount:
    def test_completed_count_starts_at_zero(self, setup):
        client, _ = setup
        data = client.get("/api/lessons").json()
        for lesson in data:
            assert lesson["completed_count"] == 0, \
                f"Lesson {lesson['id']} completed_count not 0 initially"

    def test_completed_count_increments_after_perfect_practice(self, setup):
        client, _ = setup
        # Before practice
        before = client.get("/api/lessons").json()
        lesson_1_before = next(l for l in before if l["id"] == 1)
        assert lesson_1_before["completed_count"] == 0

        # Submit a perfect dictation for sentence 1 of lesson 1
        # The sentence text is "Hi Min, you look gorgeous."
        resp = client.post("/api/practice/submit", json={
            "sentence_id": "1-01",
            "typed_text": "Hi Min, you look gorgeous."
        })
        assert resp.status_code == 200
        score = resp.json()["score"]
        assert score >= 0.7, f"Score {score} too low to count as completed"

        # After practice
        after = client.get("/api/lessons").json()
        lesson_1_after = next(l for l in after if l["id"] == 1)
        assert lesson_1_after["completed_count"] == 1, \
            f"Expected 1, got {lesson_1_after['completed_count']}"

    def test_completed_count_does_not_double_count(self, setup):
        client, _ = setup
        # Practice the same sentence twice
        client.post("/api/practice/submit", json={
            "sentence_id": "1-01",
            "typed_text": "Hi Min, you look gorgeous."
        })
        client.post("/api/practice/submit", json={
            "sentence_id": "1-01",
            "typed_text": "Hi Min, you look gorgeous."
        })

        data = client.get("/api/lessons").json()
        lesson_1 = next(l for l in data if l["id"] == 1)
        assert lesson_1["completed_count"] == 1, "Should not double-count same sentence"

    def test_completed_count_multiple_sentences(self, setup):
        client, _ = setup
        # Complete 2 different sentences in lesson 1
        client.post("/api/practice/submit", json={
            "sentence_id": "1-01",
            "typed_text": "Hi Min, you look gorgeous."
        })
        client.post("/api/practice/submit", json={
            "sentence_id": "1-02",
            "typed_text": "I am fine, thank you."
        })

        data = client.get("/api/lessons").json()
        lesson_1 = next(l for l in data if l["id"] == 1)
        assert lesson_1["completed_count"] == 2

    def test_low_score_does_not_increment_completed(self, setup):
        client, _ = setup
        # Submit a totally wrong answer - score should be < 0.7
        client.post("/api/practice/submit", json={
            "sentence_id": "1-01",
            "typed_text": "xyz completely wrong"
        })

        data = client.get("/api/lessons").json()
        lesson_1 = next(l for l in data if l["id"] == 1)
        assert lesson_1["completed_count"] == 0, \
            "Low-score practice should not increment completed_count"


# ===================================================================
# 13. Auth required: lessons endpoints without login return 401
# ===================================================================
class TestAuthRequired:
    def test_list_lessons_requires_auth(self, unauthenticated_setup):
        client, _ = unauthenticated_setup
        resp = client.get("/api/lessons")
        assert resp.status_code == 401

    def test_lesson_detail_requires_auth(self, unauthenticated_setup):
        client, _ = unauthenticated_setup
        resp = client.get("/api/lessons/1")
        assert resp.status_code == 401

    def test_sentence_detail_requires_auth(self, unauthenticated_setup):
        client, _ = unauthenticated_setup
        resp = client.get("/api/lessons/1/sentences/1")
        assert resp.status_code == 401

    def test_after_logout_requires_auth(self):
        """After logging out, endpoints should return 401."""
        client, db_path = _create_test_app()
        _seed_all_lessons(db_path)
        _register_and_login(client)

        # Confirm access works
        resp = client.get("/api/lessons")
        assert resp.status_code == 200

        # Logout
        client.post("/api/auth/logout")

        # Now should fail
        resp = client.get("/api/lessons")
        assert resp.status_code == 401
        db_path.unlink(missing_ok=True)


# ===================================================================
# Additional cross-cutting tests
# ===================================================================
class TestCrossCutting:
    def test_lesson_detail_matches_list(self, setup, lesson_data):
        """Fields in list view should match those in detail view."""
        client, _ = setup
        listing = client.get("/api/lessons").json()
        for summary in listing:
            detail = client.get(f"/api/lessons/{summary['id']}").json()
            assert summary["title"] == detail["title"]
            assert summary["title_zh"] == detail["title_zh"]
            assert summary["title_vi"] == detail["title_vi"]
            assert summary["difficulty"] == detail["difficulty"]
            assert summary["category"] == detail["category"]
            assert summary["sentence_count"] == detail["sentence_count"]

    def test_sentence_detail_matches_lesson_detail(self, setup, lesson_data):
        """Sentence fetched individually should match the one in lesson detail."""
        client, _ = setup
        for ld in lesson_data:
            lesson_detail = client.get(f"/api/lessons/{ld['id']}").json()
            for s in lesson_detail["sentences"]:
                individual = client.get(
                    f"/api/lessons/{ld['id']}/sentences/{s['index']}"
                ).json()
                assert individual["text"] == s["text"]
                assert individual["translation_zh"] == s["translation_zh"]
                assert individual["translation_vi"] == s["translation_vi"]
                assert individual["words"] == s["words"]
                assert individual["constituents"] == s["constituents"]

    def test_word_count_matches_source_json(self, setup, lesson_data):
        """Number of words per sentence should match source JSON."""
        client, _ = setup
        for ld in lesson_data:
            detail = client.get(f"/api/lessons/{ld['id']}").json()
            for api_s, src_s in zip(detail["sentences"], ld["sentences"]):
                assert len(api_s["words"]) == len(src_s["words"]), \
                    f"Word count mismatch in lesson {ld['id']} sentence {src_s['index']}"

    def test_constituent_count_matches_source_json(self, setup, lesson_data):
        client, _ = setup
        for ld in lesson_data:
            detail = client.get(f"/api/lessons/{ld['id']}").json()
            for api_s, src_s in zip(detail["sentences"], ld["sentences"]):
                assert len(api_s["constituents"]) == len(src_s["constituents"]), \
                    f"Constituent count mismatch in lesson {ld['id']} sentence {src_s['index']}"
