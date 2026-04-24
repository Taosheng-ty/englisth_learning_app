import secrets
import sqlite3
from fastapi import APIRouter, Request, Response, HTTPException
import bcrypt
from app.models import RegisterRequest, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSIONS: dict[str, int] = {}


def get_current_user_id(request: Request) -> int:
    session_id = request.cookies.get("session")
    if not session_id or session_id not in SESSIONS:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return SESSIONS[session_id]


@router.post("/register")
def register(req: RegisterRequest, request: Request):
    db = request.app.state.db_path
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, ui_language) VALUES (?, ?, ?)",
            (req.username, pw_hash, req.ui_language),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Username already exists")
    user = conn.execute("SELECT id, username, ui_language FROM users WHERE username = ?", (req.username,)).fetchone()
    conn.close()
    return {"id": user["id"], "username": user["username"], "ui_language": user["ui_language"]}


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response):
    db = request.app.state.db_path
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
    conn.close()
    if not user or not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session_id = secrets.token_hex(32)
    SESSIONS[session_id] = user["id"]
    response.set_cookie(key="session", value=session_id, httponly=True, samesite="lax")
    return {"message": "Logged in", "username": user["username"]}


@router.post("/logout")
def logout(request: Request, response: Response):
    session_id = request.cookies.get("session")
    if session_id and session_id in SESSIONS:
        del SESSIONS[session_id]
    response.delete_cookie("session")
    return {"message": "Logged out"}
