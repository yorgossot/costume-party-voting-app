import sqlite3
import time
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

from auth import get_current_user, CurrentUser
from config import COSTUMES_DIR, ALLOWED_CONTENT_TYPES, MAX_PHOTO_SIZE, MAX_PHOTO_WIDTH
from database import get_db
from routers.users import get_display_name, get_dressed_up_as

router = APIRouter(prefix="/api")


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

    old = conn.execute(
        "SELECT photo_filename FROM costumes WHERE user_id = ?", (user["user_id"],)
    ).fetchone()
    if old:
        old_path = COSTUMES_DIR / old["photo_filename"]
        if old_path.exists():
            old_path.unlink()
        conn.execute("DELETE FROM costumes WHERE user_id = ?", (user["user_id"],))

    cursor = conn.execute(
        "INSERT INTO costumes (user_id, photo_filename) VALUES (?, ?)",
        (user["user_id"], filename),
    )
    conn.commit()
    costume_id = cursor.lastrowid

    return {"costume_id": costume_id, "filename": filename}


@router.delete("/costume")
def delete_costume(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT id, photo_filename FROM costumes WHERE user_id = ?", (user["user_id"],)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="No costume found")

    conn.execute("DELETE FROM votes WHERE costume_id = ?", (row["id"],))
    conn.execute("DELETE FROM costumes WHERE id = ?", (row["id"],))
    conn.commit()

    filepath = COSTUMES_DIR / row["photo_filename"]
    if filepath.exists():
        filepath.unlink()

    return {"success": True}


@router.get("/costumes")
def list_costumes(conn: sqlite3.Connection = Depends(get_db)):
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

    return [
        {
            "id": r["id"],
            "user_id": r["user_id"],
            "photo_url": f"/static/costumes/{r['photo_filename']}",
            # "vote_count": r["vote_count"], # Uncomment to show vote counts on frontend
        }
        for r in rows
    ]
