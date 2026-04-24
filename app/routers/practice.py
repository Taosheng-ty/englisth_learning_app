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
