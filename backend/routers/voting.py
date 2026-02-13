from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, CurrentUser
from config import MAX_VOTES_PER_USER
from database import get_db

router = APIRouter(prefix="/api")


class VoteRequest(BaseModel):
    costume_id: int


@router.post("/vote")
def vote(body: VoteRequest, user: CurrentUser = Depends(get_current_user)):
    conn = get_db()

    costume = conn.execute(
        "SELECT id, user_id FROM costumes WHERE id = ?", (body.costume_id,)
    ).fetchone()
    if not costume:
        conn.close()
        raise HTTPException(status_code=404, detail="Costume not found")
    if costume["user_id"] == user["user_id"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot vote for your own costume")

    existing = conn.execute(
        "SELECT id FROM votes WHERE voter_id = ? AND costume_id = ?",
        (user["user_id"], body.costume_id),
    ).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=400, detail="Already voted for this costume")

    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM votes WHERE voter_id = ?", (user["user_id"],)
    ).fetchone()["cnt"]
    if count >= MAX_VOTES_PER_USER:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_VOTES_PER_USER} votes reached",
        )

    conn.execute(
        "INSERT INTO votes (voter_id, costume_id) VALUES (?, ?)",
        (user["user_id"], body.costume_id),
    )
    conn.commit()
    conn.close()

    return {"success": True, "votes_remaining": MAX_VOTES_PER_USER - count - 1}


@router.get("/results")
def results():
    conn = get_db()

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
