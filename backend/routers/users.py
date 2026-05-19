import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, CurrentUser
from database import get_db, get_competition_status
from config import MIN_FIELD_LENGTH, MAX_FIELD_LENGTH

router = APIRouter(prefix="/api")

USER_FIELDS = {"display_name", "dressed_up_as"}


class UserPatchRequest(BaseModel):
    display_name: str | None = None
    dressed_up_as: str | None = None


# -----------------------------------
# -------- ROUTER ENDPOINTS  --------
# -----------------------------------


@router.patch("/users/me")
def update_me(
    body: UserPatchRequest,
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Partially update the current user's profile. Send any subset of
    {display_name, dressed_up_as}; only the provided fields are changed."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result: dict = {"user_id": user["user_id"]}
    for field, value in updates.items():
        result.update(_set_user_field(field, value, user, conn))
    return result


@router.get("/users/me")
def me(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:

    row = conn.execute(
        "SELECT id, access_code, display_name, dressed_up_as, is_admin FROM users WHERE id = ?",
        (user["user_id"],),
    ).fetchone()
    costume = conn.execute(
        "SELECT id, photo_filename FROM costumes WHERE user_id = ?",
        (user["user_id"],),
    ).fetchone()
    votes = conn.execute(
        """
        SELECT c.id as costume_id
        FROM votes v
        JOIN costumes c ON c.user_id = v.voted_user_id
        WHERE v.voter_id = ?
        """,
        (user["user_id"],),
    ).fetchall()

    voted_costume_ids = [v["costume_id"] for v in votes]

    return {
        "user_id": row["id"],
        "access_code": row["access_code"],
        "display_name": row["display_name"],
        "dressed_up_as": row["dressed_up_as"],
        "is_admin": bool(row["is_admin"]),
        "costume": (
            {
                "id": costume["id"],
                "photo_url": f"/static/costumes/{costume['photo_filename']}",
            }
            if costume
            else None
        ),
        "votes_used": len(voted_costume_ids),
        "voted_costume_ids": voted_costume_ids,
    }


# -----------------------------------
# --------- HELPER FUNCTIONS --------
# -----------------------------------


def _set_user_field(
    field: str, value: str, user: CurrentUser, conn: sqlite3.Connection
) -> dict:
    """
    Helper function to set a user field (display_name or dressed_up_as) with validation.
    First-time setting is always allowed. Changing an existing value requires setup phase.
    """
    if field not in USER_FIELDS:
        raise HTTPException(status_code=400, detail=f"Unknown field: {field}")
    if not MIN_FIELD_LENGTH <= len(value) <= MAX_FIELD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"{field} must be between {MIN_FIELD_LENGTH} and {MAX_FIELD_LENGTH} characters",
        )
    row = conn.execute(
        f"SELECT {field} FROM users WHERE id = ?", (user["user_id"],)
    ).fetchone()
    if row and row[field] and get_competition_status(conn) != "setup":
        raise HTTPException(
            status_code=403, detail="Changes are only allowed during the setup phase"
        )
    conn.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user["user_id"]))
    conn.commit()
    return {"user_id": user["user_id"], field: value}


# Helper functions to get user info in other routers without repeating code
def _get_user_field(
    field: str, user: CurrentUser, conn: sqlite3.Connection
) -> str | None:
    if field not in USER_FIELDS:
        raise ValueError(f"Unknown field: {field}")
    row = conn.execute(
        f"SELECT {field} FROM users WHERE id = ?", (user["user_id"],)
    ).fetchone()
    return row[field] if row else None


def get_display_name(user: CurrentUser, conn: sqlite3.Connection) -> str | None:
    return _get_user_field("display_name", user, conn)


def get_dressed_up_as(user: CurrentUser, conn: sqlite3.Connection) -> str | None:
    return _get_user_field("dressed_up_as", user, conn)


def has_completed_profile(user: CurrentUser, conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        """
        SELECT u.display_name, u.dressed_up_as, c.id as costume_id
        FROM users u
        LEFT JOIN costumes c ON c.user_id = u.id
        WHERE u.id = ?
        """,
        (user["user_id"],),
    ).fetchone()
    return bool(
        row and row["display_name"] and row["dressed_up_as"] and row["costume_id"]
    )
