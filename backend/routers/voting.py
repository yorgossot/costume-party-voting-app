import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, CurrentUser
from config import MAX_VOTES_PER_USER, ALLOW_UNREGISTERED_VOTING
from database import get_db, get_competition_status
from .users import has_completed_profile

router = APIRouter(prefix="/api")


class VoteRequest(BaseModel):
    costume_id: int


@router.post("/vote")
def vote(
    body: VoteRequest,
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):

    # Check if voting is open
    if get_competition_status(conn) != "voting":
        raise HTTPException(status_code=403, detail="Voting is not open")

    # Check if user has completed profile if unregistered voting is not allowed
    if not ALLOW_UNREGISTERED_VOTING and not has_completed_profile(user, conn):
        raise HTTPException(
            status_code=403,
            detail="Complete your profile and upload a costume to vote",
        )

    # Verify costume exists and is not the user's own
    costume = conn.execute(
        "SELECT id, user_id FROM costumes WHERE id = ?", (body.costume_id,)
    ).fetchone()
    if not costume:
        raise HTTPException(status_code=404, detail="Costume not found")
    if costume["user_id"] == user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot vote for your own costume")

    # Use a transaction to ensure vote count integrity
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Check if user has already voted for this costume
        existing = conn.execute(
            "SELECT id FROM votes WHERE voter_id = ? AND costume_id = ?",
            (user["user_id"], body.costume_id),
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400, detail="Already voted for this costume"
            )
        # Check if user has remaining votes
        count = conn.execute(
            "SELECT COUNT(*) as cnt FROM votes WHERE voter_id = ?", (user["user_id"],)
        ).fetchone()["cnt"]
        if count >= MAX_VOTES_PER_USER:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum of {MAX_VOTES_PER_USER} votes reached",
            )
        # Insert the vote
        conn.execute(
            "INSERT INTO votes (voter_id, costume_id) VALUES (?, ?)",
            (user["user_id"], body.costume_id),
        )
        conn.commit()
    except HTTPException:
        # Rollback on any HTTPException to avoid partial updates
        conn.rollback()
        raise

    return {"success": True, "votes_remaining": MAX_VOTES_PER_USER - count - 1}


@router.post("/unvote")
def unvote(
    body: VoteRequest,
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):

    if get_competition_status(conn) != "voting":
        raise HTTPException(status_code=403, detail="Voting is not open")

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
    if get_competition_status(conn) != "reveal":
        raise HTTPException(status_code=403, detail="Results are not available yet")

    rows = conn.execute("""
        SELECT c.id as costume_id, u.access_code, u.display_name, u.dressed_up_as,
               c.photo_filename, COUNT(v.id) as vote_count
        FROM costumes c
        JOIN users u ON c.user_id = u.id
        LEFT JOIN votes v ON v.costume_id = c.id
        GROUP BY c.id
        ORDER BY vote_count DESC
        LIMIT 3
    """).fetchall()

    return [
        {
            "costume_id": r["costume_id"],
            "access_code": r["access_code"],
            "display_name": r["display_name"],
            "dressed_up_as": r["dressed_up_as"],
            "photo_url": f"/static/costumes/{r['photo_filename']}",
            "thumb_url": f"/static/costumes/thumb_{r['photo_filename']}",
            "vote_count": r["vote_count"],
        }
        for r in rows
    ]
