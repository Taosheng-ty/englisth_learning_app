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
