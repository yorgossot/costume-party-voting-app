from datetime import datetime, timedelta, timezone
from typing import TypedDict

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


@router.post("/login")
def login(body: LoginRequest):
    conn = get_db()
    row = conn.execute(
        "SELECT id, is_admin FROM users WHERE access_code = ?", (body.access_code,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="Invalid access_code")

    is_admin = bool(row["is_admin"])
    token = create_token(row["id"], body.access_code, is_admin=is_admin)
    return {"token": token, "user_id": row["id"], "is_admin": is_admin}
