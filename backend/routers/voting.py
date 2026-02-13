import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, CurrentUser
from config import MAX_VOTES_PER_USER
from database import get_db

router = APIRouter(prefix="/api")


class VoteRequest(BaseModel):
    costume_id: int


@router.post("/vote")
def vote(
    body: VoteRequest,
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):

    conn.execute("BEGIN IMMEDIATE")

    try:
        setting = conn.execute(
            "SELECT value FROM settings WHERE key = 'voting_closed'"
        ).fetchone()
        if setting and setting["value"] == "true":
            raise HTTPException(status_code=403, detail="Voting is closed")

        costume = conn.execute(
            "SELECT id, user_id FROM costumes WHERE id = ?", (body.costume_id,)
        ).fetchone()
        if not costume:
            raise HTTPException(status_code=404, detail="Costume not found")
        if costume["user_id"] == user["user_id"]:
            raise HTTPException(
                status_code=400, detail="Cannot vote for your own costume"
            )

        existing = conn.execute(
            "SELECT id FROM votes WHERE voter_id = ? AND costume_id = ?",
            (user["user_id"], body.costume_id),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400, detail="Already voted for this costume"
            )

        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM votes WHERE voter_id = ?", (user["user_id"],)
        ).fetchone()["cnt"]
        if count >= MAX_VOTES_PER_USER:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum of {MAX_VOTES_PER_USER} votes reached",
            )

        conn.execute(
            "INSERT INTO votes (voter_id, costume_id) VALUES (?, ?)",
            (user["user_id"], body.costume_id),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise

    return {"success": True, "votes_remaining": MAX_VOTES_PER_USER - count - 1}


@router.post("/unvote")
def unvote(
    body: VoteRequest,
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):

    setting = conn.execute(
        "SELECT value FROM settings WHERE key = 'voting_closed'"
    ).fetchone()
    if setting and setting["value"] == "true":
        raise HTTPException(status_code=403, detail="Voting is closed")

    costume = conn.execute(
        "SELECT id, user_id FROM costumes WHERE id = ?", (body.costume_id,)
    ).fetchone()
    if not costume:
        raise HTTPException(status_code=404, detail="Costume not found")

    existing = conn.execute(
        "SELECT id FROM votes WHERE voter_id = ? AND costume_id = ?",
        (user["user_id"], body.costume_id),
    ).fetchone()
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Cannot remove vote from costume that was not voted.",
        )

    conn.execute(
        "DELETE FROM votes WHERE voter_id = ? AND costume_id = ?",
        (user["user_id"], body.costume_id),
    )

    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM votes WHERE voter_id = ?", (user["user_id"],)
    ).fetchone()["cnt"]

    conn.commit()

    return {"success": True, "votes_remaining": MAX_VOTES_PER_USER - count}


@router.get("/results")
def results(conn: sqlite3.Connection = Depends(get_db)):
    setting = conn.execute(
        "SELECT value FROM settings WHERE key = 'voting_closed'"
    ).fetchone()
    if not setting or setting["value"] != "true":
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

    return [
        {
            "costume_id": r["costume_id"],
            "access_code": r["access_code"],
            "photo_url": f"/static/costumes/{r['photo_filename']}",
            "vote_count": r["vote_count"],
        }
        for r in rows
    ]
