import os
from pathlib import Path

MAX_VOTES_PER_USER = 5
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
MAX_PHOTO_SIZE = 60 * 1024 * 1024  # 60 MB
MAX_PHOTO_WIDTH = 1920
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/webp",
}
MIN_FIELD_LENGTH = 4
MAX_FIELD_LENGTH = 30
COSTUMES_DIR = Path(__file__).parent / "costumes"
COSTUMES_DIR.mkdir(exist_ok=True)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
FRONTEND_DIR.mkdir(exist_ok=True)
