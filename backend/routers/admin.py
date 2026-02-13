import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, CurrentUser
from config import COMPETITION_STATES
from database import get_db, get_competition_status

router = APIRouter(prefix="/api")


class SetStatusRequest(BaseModel):
    status: str


@router.get("/competition-status")
def competition_status(conn: sqlite3.Connection = Depends(get_db)):
    return {"status": get_competition_status(conn)}


@router.post("/admin/advance-status")
def advance_status(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

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


@router.post("/admin/set-status")
def set_status(
    body: SetStatusRequest,
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")

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
