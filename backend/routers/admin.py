import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Literal

from auth import require_admin
from config import COMPETITION_STATES, COSTUMES_DIR
from database import get_db, get_competition_status

UserField = Literal["display_name", "dressed_up_as", "photo"]

ATHENS_TZ = timezone(timedelta(hours=2))
PARTY_START = datetime(2026, 2, 20, 18, 0, tzinfo=ATHENS_TZ)  # Friday 6pm Greek time
PARTY_END = PARTY_START + timedelta(weeks=1)

router = APIRouter(prefix="/api")


class SetStatusRequest(BaseModel):
    status: str


def _purge_available() -> bool:
    return not (PARTY_START <= datetime.now(ATHENS_TZ) < PARTY_END)


@router.get("/competition")
def competition(conn: sqlite3.Connection = Depends(get_db)):
    return {"status": get_competition_status(conn)}


@router.put("/competition/status", dependencies=[Depends(require_admin)])
def set_competition_status(
    body: SetStatusRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Set the competition phase to an explicit value (idempotent).
    To 'advance', the client sends the next state in COMPETITION_STATES."""
    if body.status not in COMPETITION_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(COMPETITION_STATES)}",
        )

    current = get_competition_status(conn)
    conn.execute(
        "UPDATE settings SET value = ? WHERE key = 'competition_status'",
        (body.status,),
    )
    conn.commit()
    return {"status": body.status, "previous": current}


@router.get("/admin/data", dependencies=[Depends(require_admin)])
def admin_data(conn: sqlite3.Connection = Depends(get_db)):
    """State of the purgeable data set, including whether DELETE is allowed."""
    votes = conn.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    costumes = conn.execute("SELECT COUNT(*) FROM costumes").fetchone()[0]
    return {
        "purge_available": _purge_available(),
        "votes": votes,
        "costumes": costumes,
    }


@router.delete("/admin/data", dependencies=[Depends(require_admin)])
def purge(conn: sqlite3.Connection = Depends(get_db)):
    """Reset the app to a clean state for testing. Deletes all votes, costumes
    (including photo files), and resets user profiles and competition status.

    Automatically disabled between PARTY_START and PARTY_END to prevent
    accidental use during the party.
    """
    if not _purge_available():
        raise HTTPException(
            status_code=403,
            detail="Purge is disabled during the party (Friday 6pm to next Friday 6pm Greek time)",
        )

    # Delete all votes
    vote_count = conn.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    conn.execute("DELETE FROM votes")

    # Delete all costumes and their photo files
    costume_rows = conn.execute("SELECT photo_filename FROM costumes").fetchall()
    conn.execute("DELETE FROM costumes")

    # Reset user profiles
    conn.execute("UPDATE users SET display_name = NULL, dressed_up_as = NULL")

    # Reset competition status
    conn.execute("UPDATE settings SET value = 'setup' WHERE key = 'competition_status'")

    conn.commit()

    # Remove photo files and thumbnails from disk
    deleted_files = 0
    for row in costume_rows:
        path = COSTUMES_DIR / row[0]
        thumb = COSTUMES_DIR / f"thumb_{row[0]}"
        if path.exists():
            path.unlink()
            deleted_files += 1
        if thumb.exists():
            thumb.unlink()

    return {
        "purged": True,
        "votes_deleted": vote_count,
        "costumes_deleted": len(costume_rows),
        "files_deleted": deleted_files,
    }


def _get_user_by_access_code(access_code: str, conn: sqlite3.Connection):
    user = conn.execute(
        "SELECT id, display_name, dressed_up_as FROM users WHERE access_code = ?",
        (access_code,),
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/admin/users/{access_code}", dependencies=[Depends(require_admin)])
def user_lookup(access_code: str, conn: sqlite3.Connection = Depends(get_db)):
    user = _get_user_by_access_code(access_code, conn)
    costume = conn.execute(
        "SELECT id, photo_filename FROM costumes WHERE user_id = ?", (user["id"],)
    ).fetchone()
    votes_cast = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE voter_id = ?", (user["id"],)
    ).fetchone()[0]
    votes_received = conn.execute(
        "SELECT COUNT(*) FROM votes WHERE voted_user_id = ?", (user["id"],)
    ).fetchone()[0]
    return {
        "user_id": user["id"],
        "display_name": user["display_name"],
        "dressed_up_as": user["dressed_up_as"],
        "has_photo": bool(costume and costume["photo_filename"]),
        "votes_cast": votes_cast,
        "votes_received": votes_received,
    }


@router.delete(
    "/admin/users/{access_code}/fields/{field}",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def reset_user_field(
    access_code: str,
    field: UserField,
    conn: sqlite3.Connection = Depends(get_db),
):
    user = _get_user_by_access_code(access_code, conn)

    if field in ("display_name", "dressed_up_as"):
        conn.execute(f"UPDATE users SET {field} = NULL WHERE id = ?", (user["id"],))
    else:  # photo
        costume = conn.execute(
            "SELECT photo_filename FROM costumes WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if costume:
            path = COSTUMES_DIR / costume["photo_filename"]
            thumb = COSTUMES_DIR / f"thumb_{costume['photo_filename']}"
            if path.exists():
                path.unlink()
            if thumb.exists():
                thumb.unlink()
            conn.execute("DELETE FROM costumes WHERE user_id = ?", (user["id"],))

    conn.commit()
    return Response(status_code=204)


@router.delete(
    "/admin/users/{access_code}/data",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def purge_user(
    access_code: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    user = _get_user_by_access_code(access_code, conn)
    user_id = user["id"]

    conn.execute("DELETE FROM votes WHERE voter_id = ?", (user_id,))
    conn.execute("DELETE FROM votes WHERE voted_user_id = ?", (user_id,))

    costume = conn.execute(
        "SELECT photo_filename FROM costumes WHERE user_id = ?", (user_id,)
    ).fetchone()
    if costume:
        path = COSTUMES_DIR / costume["photo_filename"]
        thumb = COSTUMES_DIR / f"thumb_{costume['photo_filename']}"
        if path.exists():
            path.unlink()
        if thumb.exists():
            thumb.unlink()
        conn.execute("DELETE FROM costumes WHERE user_id = ?", (user_id,))

    conn.execute(
        "UPDATE users SET display_name = NULL, dressed_up_as = NULL WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    return Response(status_code=204)
