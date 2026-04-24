import io
import sqlite3
from datetime import date
from pathlib import Path
import edge_tts
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import DB_PATH
from app.database import init_db
from app.models import SettingsUpdate
from app.routers import auth, lessons, practice, vocabulary


def create_app(db_path: Path | None = None) -> FastAPI:
    if db_path is None:
        db_path = DB_PATH
    init_db(db_path)

    app = FastAPI(title="English Learning App")
    app.state.db_path = db_path

    class NoCacheStaticMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response = await call_next(request)
            if request.url.path.endswith(('.js', '.css', '.html')):
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response

    app.add_middleware(NoCacheStaticMiddleware)

    app.include_router(auth.router)
    app.include_router(lessons.router)
    app.include_router(practice.router)
    app.include_router(vocabulary.router)

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

    @app.get("/api/tts")
    async def tts(text: str = Query(...), rate: str = Query(default="+0%")):
        voice = "en-US-AriaNeural"
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        return StreamingResponse(buf, media_type="audio/mpeg")

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

    return app


app = create_app()
