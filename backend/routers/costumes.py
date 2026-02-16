import sqlite3
import time
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

from pathlib import Path

from auth import get_current_user, CurrentUser
from config import (
    COSTUMES_DIR,
    ALLOWED_CONTENT_TYPES,
    MAX_PHOTO_SIZE,
    MAX_PHOTO_WIDTH,
    THUMB_WIDTH,
    THUMB_QUALITY,
)
from database import get_db, get_competition_status
from routers.users import get_display_name, get_dressed_up_as

router = APIRouter(prefix="/api")


def generate_thumbnail(source_path: Path):
    img = Image.open(source_path)
    img = ImageOps.exif_transpose(img)
    if img.width > THUMB_WIDTH:
        ratio = THUMB_WIDTH / img.width
        img = img.resize((THUMB_WIDTH, int(img.height * ratio)), Image.LANCZOS)
    img = img.convert("RGB")
    thumb_path = source_path.parent / f"thumb_{source_path.name}"
    img.save(thumb_path, "JPEG", quality=THUMB_QUALITY)


@router.post("/upload-costume")
async def upload_costume(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    if not get_display_name(user, conn) or not get_dressed_up_as(user, conn):
        raise HTTPException(
            status_code=400,
            detail="Must set display name and dressed up as before uploading costume",
        )

    existing = conn.execute(
        "SELECT id FROM costumes WHERE user_id = ?", (user["user_id"],)
    ).fetchone()
    if existing and get_competition_status(conn) != "setup":
        raise HTTPException(
            status_code=403,
            detail="Costume changes are only allowed during the setup phase",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, HEIC, and WEBP images are allowed"
        )

    data = await file.read()
    if len(data) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=400, detail="Image must be under 60 MB")

    timestamp = int(time.time())
    filename = f"{user['user_id']}_{timestamp}.jpg"
    filepath = COSTUMES_DIR / filename

    img = Image.open(BytesIO(data))
    img = ImageOps.exif_transpose(img)
    if img.width > MAX_PHOTO_WIDTH:
        ratio = MAX_PHOTO_WIDTH / img.width
        img = img.resize((MAX_PHOTO_WIDTH, int(img.height * ratio)), Image.LANCZOS)
    img = img.convert("RGB")
    img.save(filepath, "JPEG", quality=85)
    generate_thumbnail(filepath)

    old = conn.execute(
        "SELECT id, photo_filename FROM costumes WHERE user_id = ?", (user["user_id"],)
    ).fetchone()
    if old:
        old_path = COSTUMES_DIR / old["photo_filename"]
        old_thumb = COSTUMES_DIR / f"thumb_{old['photo_filename']}"
        conn.execute("DELETE FROM votes WHERE costume_id = ?", (old["id"],))
        conn.execute("DELETE FROM costumes WHERE user_id = ?", (user["user_id"],))
        if old_path.exists():
            old_path.unlink()
        if old_thumb.exists():
            old_thumb.unlink()

    cursor = conn.execute(
        "INSERT INTO costumes (user_id, photo_filename) VALUES (?, ?)",
        (user["user_id"], filename),
    )
    conn.commit()
    costume_id = cursor.lastrowid

    return {"costume_id": costume_id, "filename": filename}


@router.get("/costumes")
def list_costumes(conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute("""
        SELECT c.id, c.user_id, u.access_code, u.display_name, u.dressed_up_as,
               c.photo_filename, COUNT(v.id) as vote_count
        FROM costumes c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN votes v ON v.costume_id = c.id
        GROUP BY c.id
        ORDER BY c.upload_timestamp DESC
    """).fetchall()

    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "display_name": r["display_name"],
            "dressed_up_as": r["dressed_up_as"],
            "photo_url": f"/static/costumes/{r['photo_filename']}",
            "thumb_url": f"/static/costumes/thumb_{r['photo_filename']}",
            # "vote_count": r["vote_count"], # Uncomment to show vote counts on frontend
        }
        for r in rows
    ]
