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
