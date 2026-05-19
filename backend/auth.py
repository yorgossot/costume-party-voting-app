from datetime import datetime, timedelta, timezone
from typing import TypedDict

import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS
from database import get_db

router = APIRouter(prefix="/api")
security = HTTPBearer()


class LoginRequest(BaseModel):
    access_code: str


class CurrentUser(TypedDict):
    user_id: int
    access_code: str
    is_admin: bool


def create_token(user_id: int, access_code: str, is_admin: bool = False) -> str:
    payload = {
        "sub": str(user_id),
        "access_code": access_code,
        "is_admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        user_id = int(payload["sub"])
        access_code = payload["access_code"]
        is_admin = payload.get("is_admin", False)
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"user_id": user_id, "access_code": access_code, "is_admin": is_admin}


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.post("/sessions", status_code=201)
def create_session(body: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    """Create an authenticated session (exchange an access code for a JWT)."""
    row = conn.execute(
        "SELECT id, is_admin FROM users WHERE access_code = ?", (body.access_code,)
    ).fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid access_code")

    is_admin = bool(row["is_admin"])
    token = create_token(row["id"], body.access_code, is_admin=is_admin)
    return {"token": token, "user_id": row["id"], "is_admin": is_admin}
