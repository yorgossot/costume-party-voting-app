import sqlite3
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, CurrentUser
from database import get_db

router = APIRouter(prefix="/api/admin")


@router.post("/toggle-voting")
def toggle_voting(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    current = conn.execute(
        "SELECT value FROM settings WHERE key = 'voting_closed'"
    ).fetchone()
    new_value = "false" if current and current["value"] == "true" else "true"
    conn.execute(
        "UPDATE settings SET value = ? WHERE key = 'voting_closed'", (new_value,)
    )
    conn.commit()
    return {"voting_closed": new_value == "true"}


@router.post("/toggle-result-visibility")
def toggle_result_visibility(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    current = conn.execute(
        "SELECT value FROM settings WHERE key = 'results_visible'"
    ).fetchone()
    new_value = "false" if current and current["value"] == "true" else "true"
    conn.execute(
        "UPDATE settings SET value = ? WHERE key = 'results_visible'", (new_value,)
    )
    conn.commit()
    return {"results_visible": new_value == "true"}
