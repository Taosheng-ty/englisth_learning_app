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
