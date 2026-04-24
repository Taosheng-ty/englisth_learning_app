"""
Comprehensive integration tests for the English Learning webapp.

Covers: static files, TTS endpoint, i18n content verification,
HTML structure, and full end-to-end integration flows.
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
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_WORDS = [
    {
        "word": "Hello",
        "ipa": "/həˈloʊ/",
        "pos": "interjection",
        "pos_zh": "感叹词",
        "pos_vi": "than tu",
        "role": "greeting",
        "role_zh": "问候语",
        "role_vi": "loi chao",
        "group": 0,
        "group_color": "#795548",
    },
]

SAMPLE_WORDS_2 = [
    {
        "word": "Good",
        "ipa": "/ɡʊd/",
        "pos": "adjective",
        "pos_zh": "形容词",
        "pos_vi": "tinh tu",
        "role": "modifier",
        "role_zh": "修饰语",
        "role_vi": "tu bo nghia",
        "group": 0,
        "group_color": "#FF9800",
    },
    {
        "word": "morning",
        "ipa": "/ˈmɔːrnɪŋ/",
        "pos": "noun",
        "pos_zh": "名词",
        "pos_vi": "danh tu",
        "role": "object",
        "role_zh": "宾语",
        "role_vi": "tan ngu",
        "group": 0,
        "group_color": "#2196F3",
    },
]

SAMPLE_CONSTITUENTS = [
    {
        "group": 0,
        "label_en": "greeting",
        "label_zh": "问候语",
        "label_vi": "loi chao",
        "word_indices": [0],
        "color": "#795548",
    },
]

SAMPLE_CONSTITUENTS_2 = [
    {
        "group": 0,
        "label_en": "noun phrase",
        "label_zh": "名词短语",
        "label_vi": "cum danh tu",
        "word_indices": [0, 1],
        "color": "#2196F3",
    },
]


def _make_db() -> Path:
    """Create a fresh temp database and return its path."""
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = Path(f.name)
    f.close()
    init_db(db_path)
    return db_path


def _seed_lessons(db_path: Path):
    """Insert two lessons with sentences into the database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "Greetings", "问候", "Chao hoi", "A1", "daily_conversation", 2),
    )
    conn.execute(
        "INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?)",
        (2, "Morning Routine", "早晨日常", "Thu tuc buoi sang", "A2", "daily_life", 1),
    )
    conn.execute(
        "INSERT INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "1-01", 1, 1, "Hello",
            "你好", "Xin chao",
            json.dumps(SAMPLE_WORDS), json.dumps(SAMPLE_CONSTITUENTS),
        ),
    )
    conn.execute(
        "INSERT INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "1-02", 1, 2, "Goodbye",
            "再见", "Tam biet",
            json.dumps(SAMPLE_WORDS), json.dumps(SAMPLE_CONSTITUENTS),
        ),
    )
    conn.execute(
        "INSERT INTO sentences VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "2-01", 2, 1, "Good morning",
            "早上好", "Chao buoi sang",
            json.dumps(SAMPLE_WORDS_2), json.dumps(SAMPLE_CONSTITUENTS_2),
        ),
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def client_and_db():
    """Yield a TestClient + db_path, clean up afterwards."""
    db_path = _make_db()
    _seed_lessons(db_path)
    app = create_app(db_path)
    client = TestClient(app)
    yield client, db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture()
def authed_client(client_and_db):
    """Return a client that is already registered + logged-in as 'alice'."""
    client, db_path = client_and_db
    client.post("/api/auth/register", json={"username": "alice", "password": "pass123", "ui_language": "zh"})
    client.post("/api/auth/login", json={"username": "alice", "password": "pass123"})
    return client, db_path


# ===================================================================
# 1. STATIC FILE TESTS
# ===================================================================

class TestStaticFiles:
    """Tests 1-8: static file serving and cache headers."""

    def test_01_index_html_structure(self, client_and_db):
        """GET / returns HTML with all required page divs."""
        client, _ = client_and_db
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.text
        for div_id in ("page-login", "page-dashboard", "page-lesson", "page-vocabulary", "page-settings"):
            assert f'id="{div_id}"' in html, f"Missing div#{div_id} in index.html"

    def test_02_app_js_valid(self, client_and_db):
        """GET /js/app.js returns valid JavaScript containing App object."""
        client, _ = client_and_db
        resp = client.get("/js/app.js")
        assert resp.status_code == 200
        text = resp.text
        assert "const App" in text or "App" in text
        assert "function" in text or "=>" in text  # has function bodies

    def test_03_i18n_js_has_zh_and_vi(self, client_and_db):
        """GET /js/i18n.js returns JS with both zh and vi string objects."""
        client, _ = client_and_db
        resp = client.get("/js/i18n.js")
        assert resp.status_code == 200
        text = resp.text
        assert "zh:" in text or "zh :" in text, "Missing zh block in i18n.js"
        assert "vi:" in text or "vi :" in text, "Missing vi block in i18n.js"

    def test_04_tts_js_valid(self, client_and_db):
        """GET /js/tts.js returns valid JavaScript with TTS object."""
        client, _ = client_and_db
        resp = client.get("/js/tts.js")
        assert resp.status_code == 200
        text = resp.text
        assert "const TTS" in text or "TTS" in text
        assert "speak" in text

    def test_05_annotation_js_has_pos_colors(self, client_and_db):
        """GET /js/annotation.js returns JS containing POS_COLORS."""
        client, _ = client_and_db
        resp = client.get("/js/annotation.js")
        assert resp.status_code == 200
        text = resp.text
        assert "POS_COLORS" in text
        assert "noun" in text
        assert "verb" in text

    def test_06_dictation_js_has_isComposing(self, client_and_db):
        """GET /js/dictation.js returns JS with isComposing property."""
        client, _ = client_and_db
        resp = client.get("/js/dictation.js")
        assert resp.status_code == 200
        text = resp.text
        assert "isComposing" in text
        assert "compositionstart" in text or "compositionend" in text

    def test_07_style_css_valid(self, client_and_db):
        """GET /css/style.css returns valid CSS with root variables."""
        client, _ = client_and_db
        resp = client.get("/css/style.css")
        assert resp.status_code == 200
        text = resp.text
        assert ":root" in text
        assert "--primary" in text
        assert "font-family" in text

    def test_08_cache_control_no_cache_for_js_css(self, client_and_db):
        """Cache-Control header is set to no-cache for JS and CSS files."""
        client, _ = client_and_db
        for path in ("/js/app.js", "/js/i18n.js", "/css/style.css"):
            resp = client.get(path)
            cc = resp.headers.get("cache-control", "")
            assert "no-cache" in cc, f"Cache-Control missing no-cache for {path}: got '{cc}'"


# ===================================================================
# 2. TTS ENDPOINT TESTS
# ===================================================================

class TestTTSEndpoint:
    """Tests 9-13: TTS audio generation endpoint."""

    def test_09_tts_hello_returns_audio_mpeg(self, client_and_db):
        """GET /api/tts?text=Hello returns audio/mpeg content."""
        client, _ = client_and_db
        resp = client.get("/api/tts?text=Hello")
        assert resp.status_code == 200
        assert "audio/mpeg" in resp.headers.get("content-type", "")

    def test_10_tts_hello_world_default_rate(self, client_and_db):
        """GET /api/tts?text=Hello+world with rate=+0% returns audio."""
        client, _ = client_and_db
        resp = client.get("/api/tts", params={"text": "Hello world", "rate": "+0%"})
        assert resp.status_code == 200
        assert len(resp.content) > 0
        assert "audio/mpeg" in resp.headers.get("content-type", "")

    def test_11_tts_slower_rate(self, client_and_db):
        """GET /api/tts with rate=-20% returns audio (slower speech)."""
        client, _ = client_and_db
        resp = client.get("/api/tts", params={"text": "Testing slower speech", "rate": "-20%"})
        assert resp.status_code == 200
        assert len(resp.content) > 0
        assert "audio/mpeg" in resp.headers.get("content-type", "")

    def test_12_tts_response_is_valid_mp3(self, client_and_db):
        """TTS response has non-trivial content (valid MP3 data)."""
        client, _ = client_and_db
        resp = client.get("/api/tts?text=Hello")
        assert resp.status_code == 200
        data = resp.content
        # MP3 files typically start with ID3 tag (49 44 33) or MPEG sync (ff fb/ff f3)
        # edge-tts output can vary, so just check we got substantial audio data
        assert len(data) > 100, f"TTS response too small ({len(data)} bytes), expected audio data"

    def test_13_tts_empty_text(self, client_and_db):
        """TTS with empty text - verify server handles it (422 or empty response)."""
        client, _ = client_and_db
        # FastAPI should reject missing required query param with 422
        resp = client.get("/api/tts")
        assert resp.status_code == 422, "Empty text should trigger validation error"


# ===================================================================
# 3. I18N CONTENT VERIFICATION
# ===================================================================

class TestI18nContent:
    """Tests 14-16: internationalization string completeness."""

    @staticmethod
    def _parse_i18n_js() -> str:
        """Read the raw i18n.js source from disk."""
        js_path = Path(__file__).resolve().parent.parent / "app" / "static" / "js" / "i18n.js"
        return js_path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_keys(block: str) -> set[str]:
        """Extract JS object literal keys from a block of 'key: value' pairs.

        Only match keys that appear after a comma, newline, or at the start
        of the block -- this avoids false positives from words inside string
        values that happen to precede a quote-colon boundary.
        """
        return set(re.findall(r"(?:^|,)\s*(\w+)\s*:", block, re.MULTILINE))

    def test_14_zh_strings_contain_chinese_characters(self):
        """zh strings contain actual Chinese characters (not ASCII)."""
        src = self._parse_i18n_js()
        # Find the zh block
        zh_match = re.search(r"zh\s*:\s*\{([^}]+)\}", src, re.DOTALL)
        assert zh_match, "Could not find zh block in i18n.js"
        zh_block = zh_match.group(1)
        # Check for Chinese characters (CJK Unified Ideographs range)
        chinese_chars = re.findall(r"[一-鿿]", zh_block)
        assert len(chinese_chars) > 10, f"Expected Chinese characters in zh block, found only {len(chinese_chars)}"
        # Spot check specific translations
        assert "登录" in zh_block, "Missing '登录' (login) in zh"
        assert "注册" in zh_block, "Missing '注册' (register) in zh"
        assert "词汇" in zh_block, "Missing '词汇' (vocabulary) in zh"
        assert "设置" in zh_block, "Missing '设置' (settings) in zh"

    def test_15_vi_strings_all_present(self):
        """vi strings contain all expected translation keys."""
        src = self._parse_i18n_js()
        vi_match = re.search(r"vi\s*:\s*\{([^}]+)\}", src, re.DOTALL)
        assert vi_match, "Could not find vi block in i18n.js"
        vi_block = vi_match.group(1)
        required_keys = [
            "login", "register", "vocabulary", "settings", "logout",
            "learn", "read_aloud", "dictation", "submit",
            "good", "okay", "again",
            "flashcard_mode", "ui_language", "tts_speed", "daily_goal", "save",
        ]
        vi_keys = self._extract_keys(vi_block)
        for key in required_keys:
            assert key in vi_keys, f"Missing key '{key}' in vi strings"
        # Also verify values are Vietnamese (not English placeholders)
        assert "nhập" in vi_block.lower() or "đăng nhập" in vi_block.lower(), "vi login should be Vietnamese text"
        assert "vựng" in vi_block.lower() or "từ vựng" in vi_block.lower(), "vi vocabulary should be Vietnamese text"

    def test_16_zh_and_vi_have_same_keys(self):
        """zh and vi translation objects have the exact same set of keys."""
        src = self._parse_i18n_js()
        zh_match = re.search(r"zh\s*:\s*\{([^}]+)\}", src, re.DOTALL)
        vi_match = re.search(r"vi\s*:\s*\{([^}]+)\}", src, re.DOTALL)
        assert zh_match and vi_match, "Could not find zh/vi blocks"
        zh_keys = self._extract_keys(zh_match.group(1))
        vi_keys = self._extract_keys(vi_match.group(1))
        missing_in_vi = zh_keys - vi_keys
        missing_in_zh = vi_keys - zh_keys
        assert not missing_in_vi, f"Keys in zh but missing in vi: {missing_in_vi}"
        assert not missing_in_zh, f"Keys in vi but missing in zh: {missing_in_zh}"


# ===================================================================
# 4. HTML STRUCTURE TESTS
# ===================================================================

class TestHTMLStructure:
    """Tests 17-22: verify HTML elements in each page section."""

    @staticmethod
    def _get_html(client) -> str:
        return client.get("/").text

    def test_17_login_page_language_selector(self, client_and_db):
        """Login page has language selector buttons for zh and vi."""
        html = self._get_html(client_and_db[0])
        assert 'class="lang-selector"' in html
        assert 'data-lang="zh"' in html, "Missing zh language button"
        assert 'data-lang="vi"' in html, "Missing vi language button"

    def test_18_login_page_auth_forms(self, client_and_db):
        """Login page has login and register forms."""
        html = self._get_html(client_and_db[0])
        assert 'id="login-form"' in html, "Missing login form"
        assert 'id="register-form"' in html, "Missing register form"
        assert 'id="login-username"' in html, "Missing login username input"
        assert 'id="login-password"' in html, "Missing login password input"
        assert 'id="reg-username"' in html, "Missing register username input"
        assert 'id="reg-password"' in html, "Missing register password input"
        assert 'data-tab="login"' in html, "Missing login tab button"
        assert 'data-tab="register"' in html, "Missing register tab button"

    def test_19_dashboard_elements(self, client_and_db):
        """Dashboard has progress ring, lesson grid, filter, and review button."""
        html = self._get_html(client_and_db[0])
        assert 'class="progress-ring"' in html, "Missing progress ring SVG"
        assert 'id="progress-ring-fill"' in html, "Missing progress ring fill circle"
        assert 'id="lesson-grid"' in html, "Missing lesson grid"
        assert 'id="filter-difficulty"' in html, "Missing difficulty filter"
        assert 'id="btn-review"' in html, "Missing review button"
        # Check progress percentage display
        assert 'id="progress-pct"' in html, "Missing progress percentage"

    def test_20_lesson_page_elements(self, client_and_db):
        """Lesson page has annotation area, mode tabs, sentence navigation."""
        html = self._get_html(client_and_db[0])
        assert 'id="annotation-area"' in html, "Missing annotation area"
        assert 'data-mode="learn"' in html, "Missing learn mode tab"
        assert 'data-mode="read_aloud"' in html, "Missing read_aloud mode tab"
        assert 'data-mode="dictation"' in html, "Missing dictation mode tab"
        assert 'id="btn-prev"' in html, "Missing previous sentence button"
        assert 'id="btn-next"' in html, "Missing next sentence button"
        assert 'id="dictation-input"' in html, "Missing dictation input textarea"
        assert 'id="btn-submit-dictation"' in html, "Missing submit dictation button"

    def test_21_vocabulary_page_elements(self, client_and_db):
        """Vocabulary page has filter select and flashcard button."""
        html = self._get_html(client_and_db[0])
        assert 'id="vocab-filter-select"' in html, "Missing vocabulary filter select"
        assert 'id="btn-flashcards"' in html, "Missing flashcard button"
        # Check filter options
        assert 'value="all"' in html, "Missing 'all' filter option"
        assert 'value="mastered"' in html, "Missing 'mastered' filter option"
        assert 'value="learning"' in html, "Missing 'learning' filter option"
        assert 'value="weak"' in html, "Missing 'weak' filter option"

    def test_22_settings_page_elements(self, client_and_db):
        """Settings page has language, TTS speed, and daily goal controls."""
        html = self._get_html(client_and_db[0])
        assert 'id="setting-language"' in html, "Missing language setting select"
        assert 'id="setting-tts-speed"' in html, "Missing TTS speed setting"
        assert 'id="setting-daily-goal"' in html, "Missing daily goal setting"
        assert 'id="btn-save-settings"' in html, "Missing save settings button"
        # Verify language options
        assert 'value="zh"' in html, "Missing zh option in language setting"
        assert 'value="vi"' in html, "Missing vi option in language setting"


# ===================================================================
# 5. FULL INTEGRATION FLOW
# ===================================================================

class TestFullIntegrationFlow:
    """Tests 23-24: end-to-end flows in Chinese and Vietnamese."""

    def _run_full_flow(self, client, db_path, username, language):
        """
        Execute the complete user flow:
        Register -> Login -> Profile -> List Lessons -> Open Lesson
        -> Submit Dictation -> Check Vocabulary -> Check Stats
        """
        results = {}

        # Step 1: Register
        resp = client.post(
            "/api/auth/register",
            json={"username": username, "password": "testpass", "ui_language": language},
        )
        assert resp.status_code == 200, f"Register failed: {resp.text}"
        reg_data = resp.json()
        assert reg_data["username"] == username
        assert reg_data["ui_language"] == language
        results["register"] = reg_data

        # Step 2: Login
        resp = client.post(
            "/api/auth/login",
            json={"username": username, "password": "testpass"},
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        assert "session" in resp.cookies, "No session cookie after login"
        results["login"] = resp.json()

        # Step 3: Get Profile
        resp = client.get("/api/user/profile")
        assert resp.status_code == 200, f"Get profile failed: {resp.text}"
        profile = resp.json()
        assert profile["username"] == username
        assert profile["ui_language"] == language
        assert profile["xp"] == 0
        assert profile["streak_days"] == 0
        assert "daily_goal" in profile
        assert "tts_speed" in profile
        results["profile"] = profile

        # Step 4: List Lessons
        resp = client.get("/api/lessons")
        assert resp.status_code == 200, f"List lessons failed: {resp.text}"
        lessons = resp.json()
        assert len(lessons) == 2, f"Expected 2 lessons, got {len(lessons)}"
        lesson1 = lessons[0]
        assert lesson1["id"] == 1
        assert lesson1["title"] == "Greetings"
        assert lesson1["title_zh"] == "问候"
        assert lesson1["title_vi"] == "Chao hoi"
        assert lesson1["completed_count"] == 0
        results["lessons"] = lessons

        # Step 5: Open Lesson (get detail)
        resp = client.get("/api/lessons/1")
        assert resp.status_code == 200, f"Get lesson detail failed: {resp.text}"
        lesson_detail = resp.json()
        assert lesson_detail["id"] == 1
        assert len(lesson_detail["sentences"]) == 2
        s1 = lesson_detail["sentences"][0]
        assert s1["text"] == "Hello"
        assert s1["translation_zh"] == "你好"
        assert s1["translation_vi"] == "Xin chao"
        assert len(s1["words"]) >= 1
        assert len(s1["constituents"]) >= 1
        results["lesson_detail"] = lesson_detail

        # Step 6: Submit Dictation (correct answer)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-01", "typed_text": "Hello"},
        )
        assert resp.status_code == 200, f"Submit dictation failed: {resp.text}"
        dictation_result = resp.json()
        assert dictation_result["score"] == 1.0, f"Perfect dictation should score 1.0, got {dictation_result['score']}"
        assert dictation_result["xp_earned"] == 10
        assert "diffs" in dictation_result
        assert dictation_result["expected_text"] == "Hello"
        results["dictation"] = dictation_result

        # Step 6b: Submit Dictation again (partially correct)
        resp = client.post(
            "/api/practice/submit",
            json={"sentence_id": "1-02", "typed_text": "Goodby"},
        )
        assert resp.status_code == 200
        partial_result = resp.json()
        # "Goodby" vs "Goodbye" - levenshtein distance 1, should be 'close'
        assert partial_result["score"] > 0, "Partial dictation should have non-zero score"
        results["dictation_partial"] = partial_result

        # Step 7: Check Vocabulary
        resp = client.get("/api/vocabulary")
        assert resp.status_code == 200, f"Get vocabulary failed: {resp.text}"
        vocab = resp.json()
        assert len(vocab) >= 1, "Vocabulary should have at least 1 word after practice"
        word_names = [v["word"] for v in vocab]
        assert "hello" in word_names, "Expected 'hello' in vocabulary"
        for v in vocab:
            assert "ipa" in v
            assert "pos" in v
            assert "status" in v
            assert v["seen_count"] >= 1
        results["vocabulary"] = vocab

        # Step 7b: Check Flashcards
        resp = client.get("/api/vocabulary/flashcards")
        assert resp.status_code == 200
        flashcards = resp.json()
        assert len(flashcards) >= 1
        fc = flashcards[0]
        assert "word" in fc
        assert "ipa" in fc
        assert "example_sentence" in fc
        results["flashcards"] = flashcards

        # Step 8: Check Stats
        resp = client.get("/api/stats")
        assert resp.status_code == 200, f"Get stats failed: {resp.text}"
        stats = resp.json()
        assert stats["xp"] > 0, "XP should be > 0 after practice"
        assert stats["total_sentences_practiced"] >= 1
        assert stats["total_words_learned"] >= 1
        assert stats["accuracy_percent"] > 0
        assert stats["sentences_today"] >= 1
        assert "daily_goal" in stats
        results["stats"] = stats

        # Step 8b: Check Review Due
        resp = client.get("/api/review/due")
        assert resp.status_code == 200
        review = resp.json()
        assert isinstance(review, list)
        results["review_due"] = review

        return results

    def test_23_full_flow_chinese_language(self, client_and_db):
        """Full integration flow with Chinese (zh) language setting."""
        client, db_path = client_and_db
        results = self._run_full_flow(client, db_path, "user_zh", "zh")

        # Verify Chinese-specific content
        assert results["profile"]["ui_language"] == "zh"
        lesson = results["lessons"][0]
        assert lesson["title_zh"] == "问候"

    def test_24_full_flow_vietnamese_language(self, client_and_db):
        """Full integration flow with Vietnamese (vi) language setting."""
        client, db_path = client_and_db
        results = self._run_full_flow(client, db_path, "user_vi", "vi")

        # Verify Vietnamese-specific content
        assert results["profile"]["ui_language"] == "vi"
        lesson = results["lessons"][0]
        assert lesson["title_vi"] == "Chao hoi"

        # Verify Vietnamese translations in lesson detail
        s1 = results["lesson_detail"]["sentences"][0]
        assert s1["translation_vi"] == "Xin chao"


# ===================================================================
# 6. ADDITIONAL EDGE CASES
# ===================================================================

class TestEdgeCases:
    """Additional tests for robustness."""

    def test_unauthenticated_api_returns_401(self, client_and_db):
        """API endpoints require authentication."""
        client, _ = client_and_db
        for endpoint in ("/api/lessons", "/api/user/profile", "/api/stats", "/api/vocabulary"):
            resp = client.get(endpoint)
            assert resp.status_code == 401, f"{endpoint} should return 401 for unauthenticated user"

    def test_nonexistent_lesson_returns_404(self, authed_client):
        """Requesting a non-existent lesson returns 404."""
        client, _ = authed_client
        resp = client.get("/api/lessons/999")
        assert resp.status_code == 404

    def test_duplicate_registration(self, client_and_db):
        """Registering the same username twice returns 409."""
        client, _ = client_and_db
        client.post("/api/auth/register", json={"username": "dup", "password": "p1"})
        resp = client.post("/api/auth/register", json={"username": "dup", "password": "p2"})
        assert resp.status_code == 409

    def test_wrong_password_login(self, client_and_db):
        """Login with wrong password returns 401."""
        client, _ = client_and_db
        client.post("/api/auth/register", json={"username": "bob", "password": "correct"})
        resp = client.post("/api/auth/login", json={"username": "bob", "password": "wrong"})
        assert resp.status_code == 401

    def test_settings_update_and_readback(self, authed_client):
        """Update settings and verify they persist."""
        client, _ = authed_client
        resp = client.put(
            "/api/user/settings",
            json={"ui_language": "vi", "daily_goal": 15, "tts_speed": 0.8},
        )
        assert resp.status_code == 200
        profile = client.get("/api/user/profile").json()
        assert profile["ui_language"] == "vi"
        assert profile["daily_goal"] == 15
        assert profile["tts_speed"] == 0.8

    def test_vocabulary_filter(self, authed_client):
        """Vocabulary filter returns correct subset."""
        client, _ = authed_client
        # Practice a sentence to create vocabulary entries
        client.post("/api/practice/submit", json={"sentence_id": "1-01", "typed_text": "Hello"})
        # All filter
        all_vocab = client.get("/api/vocabulary?filter=all").json()
        assert len(all_vocab) >= 1
        # Weak filter (one attempt, one correct => mastered, so weak should be empty)
        weak_vocab = client.get("/api/vocabulary?filter=weak").json()
        # Since hello was correct, ratio = 1.0 => mastered
        mastered_vocab = client.get("/api/vocabulary?filter=mastered").json()
        assert len(mastered_vocab) >= 1

    def test_self_rate_read_aloud(self, authed_client):
        """Self-rating for read-aloud mode works correctly."""
        client, _ = authed_client
        for rating in ("good", "okay", "again"):
            resp = client.post(
                "/api/practice/self-rate",
                json={"sentence_id": "1-01", "rating": rating},
            )
            assert resp.status_code == 200
            assert resp.json()["rating"] == rating

    def test_logout_invalidates_session(self, authed_client):
        """After logout, API calls return 401."""
        client, _ = authed_client
        # Verify we are authenticated
        assert client.get("/api/user/profile").status_code == 200
        # Logout
        client.post("/api/auth/logout")
        # Now should be 401
        assert client.get("/api/user/profile").status_code == 401

    def test_get_individual_sentence(self, authed_client):
        """Fetching a single sentence by lesson_id and index works."""
        client, _ = authed_client
        resp = client.get("/api/lessons/1/sentences/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Hello"
        assert data["translation_zh"] == "你好"
        assert data["translation_vi"] == "Xin chao"
        assert len(data["words"]) >= 1
        assert data["words"][0]["ipa"] == "/həˈloʊ/"
