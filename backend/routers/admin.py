from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user, CurrentUser
from database import get_db

router = APIRouter(prefix="/api/admin")


@router.post("/toggle-voting")
def toggle_voting(user: CurrentUser = Depends(get_current_user)):
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
