from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, CurrentUser
from database import get_db
from config import MIN_FIELD_LENGTH, MAX_FIELD_LENGTH

router = APIRouter(prefix="/api")

USER_FIELDS = {"display_name", "dressed_up_as"}


class UserFieldRequest(BaseModel):
    value: str


def _set_user_field(field: str, value: str, user: CurrentUser) -> dict:
    """
    Helper function to set a user field (display_name or dressed_up_as) with validation.
    Ensures the field is valid, the value is the correct length, and that the field is
    not already set (users cannot change these once set).
    """
    if field not in USER_FIELDS:
        raise HTTPException(status_code=400, detail=f"Unknown field: {field}")
    if not MIN_FIELD_LENGTH <= len(value) <= MAX_FIELD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"{field} must be between {MIN_FIELD_LENGTH} and {MAX_FIELD_LENGTH} characters",
        )
    conn = get_db()
    row = conn.execute(
        f"SELECT {field} FROM users WHERE id = ?", (user["user_id"],)
    ).fetchone()
    if row and row[field]:
        raise HTTPException(
            status_code=400, detail=f"{field} already set and cannot be changed"
        )
    conn.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user["user_id"]))
    conn.commit()
    conn.close()
    return {"user_id": user["user_id"], field: value}


# API endpoints for users to set their display name and dressed up as fields, which are
# required for voting and uploading costumes.
@router.post("/select-display-name")
def select_display_name(
    body: UserFieldRequest, user: CurrentUser = Depends(get_current_user)
):
    return _set_user_field("display_name", body.value, user)


@router.post("/select-dressed-up-as")
def select_dressed_up_as(
    body: UserFieldRequest, user: CurrentUser = Depends(get_current_user)
):
    return _set_user_field("dressed_up_as", body.value, user)


# Helper functions to get user info in other routers without repeating code
def _get_user_field(field: str, user: CurrentUser) -> str | None:
    if field not in USER_FIELDS:
        raise ValueError(f"Unknown field: {field}")
    conn = get_db()
    row = conn.execute(
        f"SELECT {field} FROM users WHERE id = ?", (user["user_id"],)
    ).fetchone()
    conn.close()
    return row[field] if row else None


def get_display_name(user: CurrentUser) -> str | None:
    return _get_user_field("display_name", user)


def get_dressed_up_as(user: CurrentUser) -> str | None:
    return _get_user_field("dressed_up_as", user)
