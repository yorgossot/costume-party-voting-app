from fileinput import filename
import os
import time
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()
from pydantic import BaseModel

from database import get_db, init_db

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MAX_VOTES_PER_USER = 5
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
MAX_PHOTO_SIZE = 60 * 1024 * 1024  # 60 MB
MAX_PHOTO_WIDTH = 1920
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/webp",
}

COSTUMES_DIR = Path(__file__).parent / "costumes"
COSTUMES_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="Party Costume Voting", lifespan=lifespan)

app.mount("/static/costumes", StaticFiles(directory=str(COSTUMES_DIR)), name="costumes")

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
FRONTEND_DIR.mkdir(exist_ok=True)

security = HTTPBearer()


# ---------------------------------------------------------------------------
# Pydantic models and types
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    access_code: str


class VoteRequest(BaseModel):
    costume_id: int

class DisplayNameRequest(BaseModel):
    display_name: str

class CurrentUser(TypedDict):
    user_id: int
    access_code: str
    is_admin: bool


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def create_token(user_id: int, access_code: str, is_admin: bool = False) -> str:
    payload = {
        "sub": str(user_id),
        "access_code": access_code,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        user_id = int(payload["sub"])
        access_code = payload["access_code"]
        is_admin = payload.get("is_admin", False)
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"user_id": user_id, "access_code": access_code, "is_admin": is_admin}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.post("/api/login")
def login(body: LoginRequest):
    conn = get_db()
    row = conn.execute(
        "SELECT id, is_admin FROM users WHERE access_code = ?", (body.access_code,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid access_code")

    is_admin = bool(row["is_admin"])
    token = create_token(row["id"], body.access_code, is_admin=is_admin)
    return {"token": token, "user_id": row["id"], "is_admin": is_admin}


# ---------------------------------------------------------------------------
# Display name endpoints
# ---------------------------------------------------------------------------
@app.post("/api/select-display-name")
async def select_display_name(
    body: DisplayNameRequest,
    user: CurrentUser = Depends(get_current_user),
):
    # Validate display name length
    if not 3 < len(body.display_name) < 31:
        raise HTTPException(
            status_code=400, detail="Display name must be between 4 and 30 characters"
        )

    conn = get_db()
    # Update display name for the user
    conn.execute(
        "UPDATE users SET display_name = ? WHERE id = ?",
        (body.display_name, user["user_id"]),
    )
    conn.commit()
    conn.close()

    return {"user_id": user["user_id"], "display_name": body.display_name}


def get_display_name(user: CurrentUser) -> str | None:
    conn = get_db()
    row = conn.execute(
        "SELECT display_name FROM users WHERE id = ?", (user["user_id"],)
    ).fetchone()
    conn.close()
    return row["display_name"] if row else None


# ---------------------------------------------------------------------------
# Costume endpoints
# ---------------------------------------------------------------------------
@app.post("/api/upload-costume")
async def upload_costume(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, HEIC, and WEBP images are allowed"
        )

    # Read and validate size
    data = await file.read()
    if len(data) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 60 MB")

    # Generate filename
    timestamp = int(time.time())
    filename = f"{user['user_id']}_{timestamp}.jpg"
    filepath = COSTUMES_DIR / filename

    # Resize and save
    from io import BytesIO

    img = Image.open(BytesIO(data))
    if img.width > MAX_PHOTO_WIDTH:
        ratio = MAX_PHOTO_WIDTH / img.width
        img = img.resize((MAX_PHOTO_WIDTH, int(img.height * ratio)), Image.LANCZOS)
    img = img.convert("RGB")
    img.save(filepath, "JPEG", quality=85)

    conn = get_db()

    # Delete old costume file if exists
    old = conn.execute(
        "SELECT photo_filename FROM costumes WHERE user_id = ?", (user["user_id"],)
    ).fetchone()
    if old:
        old_path = COSTUMES_DIR / old["photo_filename"]
        if old_path.exists():
            old_path.unlink()
        conn.execute("DELETE FROM costumes WHERE user_id = ?", (user["user_id"],))

    # Insert new costume
    cursor = conn.execute(
        "INSERT INTO costumes (user_id, photo_filename) VALUES (?, ?)",
        (user["user_id"], filename),
    )
    conn.commit()
    costume_id = cursor.lastrowid
    conn.close()

    return {"costume_id": costume_id, "filename": filename}


@app.delete("/api/costume")
def delete_costume(user: dict = Depends(get_current_user)):
    conn = get_db()
    row = conn.execute(
        "SELECT id, photo_filename FROM costumes WHERE user_id = ?", (user["user_id"],)
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="No costume found")

    # Delete votes for this costume
    conn.execute("DELETE FROM votes WHERE costume_id = ?", (row["id"],))
    # Delete costume record
    conn.execute("DELETE FROM costumes WHERE id = ?", (row["id"],))
    conn.commit()
    conn.close()

    # Delete file
    filepath = COSTUMES_DIR / row["photo_filename"]
    if filepath.exists():
        filepath.unlink()

    return {"success": True}


@app.get("/api/costumes")
def list_costumes():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT c.id, c.user_id, u.access_code, c.photo_filename,
               COUNT(v.id) as vote_count
        FROM costumes c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN votes v ON v.costume_id = c.id
        GROUP BY c.id
        ORDER BY c.upload_timestamp DESC
    """
    ).fetchall()
    conn.close()

    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "photo_url": f"/static/costumes/{r['photo_filename']}",
            "vote_count": r["vote_count"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Voting endpoints
# ---------------------------------------------------------------------------
@app.post("/api/vote")
def vote(body: VoteRequest, user: dict = Depends(get_current_user)):
    conn = get_db()

    # Check costume exists and is not the voter's own
    costume = conn.execute(
        "SELECT id, user_id FROM costumes WHERE id = ?", (body.costume_id,)
    ).fetchone()
    if not costume:
        conn.close()
        raise HTTPException(status_code=404, detail="Costume not found")
    if costume["user_id"] == user["user_id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot vote for your own costume")

    # Check for duplicate vote
    existing = conn.execute(
        "SELECT id FROM votes WHERE voter_id = ? AND costume_id = ?",
        (user["user_id"], body.costume_id),
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Already voted for this costume")

    # Check vote count
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM votes WHERE voter_id = ?", (user["user_id"],)
    ).fetchone()["cnt"]
    if count >= MAX_VOTES_PER_USER:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_VOTES_PER_USER} votes reached",
        )

    # Insert vote
    conn.execute(
        "INSERT INTO votes (voter_id, costume_id) VALUES (?, ?)",
        (user["user_id"], body.costume_id),
    )
    conn.commit()
    conn.close()

    return {"success": True, "votes_remaining": MAX_VOTES_PER_USER - count - 1}


@app.get("/api/results")
def results():
    conn = get_db()

    # Check if voting is closed
    setting = conn.execute(
        "SELECT value FROM settings WHERE key = 'voting_closed'"
    ).fetchone()
    if not setting or setting["value"] != "true":
        conn.close()
        raise HTTPException(status_code=403, detail="Results are not available yet")

    rows = conn.execute(
        """
        SELECT c.id as costume_id, u.access_code, c.photo_filename,
               COUNT(v.id) as vote_count
        FROM costumes c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN votes v ON v.costume_id = c.id
        GROUP BY c.id
        ORDER BY vote_count DESC
    """
    ).fetchall()
    conn.close()

    return [
        {
            "costume_id": r["costume_id"],
            "access_code": r["access_code"],
            "photo_url": f"/static/costumes/{r['photo_filename']}",
            "vote_count": r["vote_count"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
@app.post("/api/admin/toggle-voting")
def toggle_voting(user: dict = Depends(get_current_user)):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    conn = get_db()
    current = conn.execute(
        "SELECT value FROM settings WHERE key = 'voting_closed'"
    ).fetchone()
    new_value = "false" if current and current["value"] == "true" else "true"
    conn.execute(
        "UPDATE settings SET value = ? WHERE key = 'voting_closed'", (new_value,)
    )
    conn.commit()
    conn.close()
    return {"voting_closed": new_value == "true"}


# ---------------------------------------------------------------------------
# Frontend (must be last — catch-all mount)
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
