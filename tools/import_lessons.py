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
