import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import require_admin
from config import COMPETITION_STATES, COSTUMES_DIR
from database import get_db, get_competition_status

ATHENS_TZ = timezone(timedelta(hours=2))
PARTY_START = datetime(2026, 2, 20, 18, 0, tzinfo=ATHENS_TZ)  # Friday 6pm Greek time
PARTY_END = PARTY_START + timedelta(weeks=1)

router = APIRouter(prefix="/api")


class SetStatusRequest(BaseModel):
    status: str


@router.get("/competition-status")
def competition_status(conn: sqlite3.Connection = Depends(get_db)):
    return {"status": get_competition_status(conn)}


@router.post("/admin/advance-status", dependencies=[Depends(require_admin)])
def advance_status(conn: sqlite3.Connection = Depends(get_db)):
    current = get_competition_status(conn)
    idx = COMPETITION_STATES.index(current)

    if idx >= len(COMPETITION_STATES) - 1:
        raise HTTPException(status_code=400, detail="Already at final state")

    new_status = COMPETITION_STATES[idx + 1]
    conn.execute(
        "UPDATE settings SET value = ? WHERE key = 'competition_status'",
        (new_status,),
    )
    conn.commit()
    return {"status": new_status, "previous": current}


@router.post("/admin/set-status", dependencies=[Depends(require_admin)])
def set_status(
    body: SetStatusRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
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


@router.get("/admin/purge-available", dependencies=[Depends(require_admin)])
def purge_available():
    now = datetime.now(ATHENS_TZ)
    return {"available": not (PARTY_START <= now < PARTY_END)}


@router.post("/admin/purge", dependencies=[Depends(require_admin)])
def purge(conn: sqlite3.Connection = Depends(get_db)):
    """Reset the app to a clean state for testing. Deletes all votes, costumes
    (including photo files), and resets user profiles and competition status.

    Automatically disabled between PARTY_START and PARTY_END to prevent
    accidental use during the party.
    """
    if PARTY_START <= datetime.now(ATHENS_TZ) < PARTY_END:
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
