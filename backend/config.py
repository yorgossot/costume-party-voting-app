import os
from pathlib import Path

# --------- GENERAL CONFIGURATION ---------
MAX_VOTES_PER_USER = 5
COMPETITION_STATES = ["setup", "voting", "counting", "reveal"]
MAX_PHOTO_SIZE = 60 * 1024 * 1024  # 60 MB
MAX_PHOTO_WIDTH = 1920
MIN_FIELD_LENGTH = 4
MAX_FIELD_LENGTH = 30
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/heic",
    "image/heif",
    "image/webp",
}

# --------- JWT CONFIGURATION ---------
JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
# Fail if JWT_SECRET is not set in production environments, but allow a default for
# local development
if not JWT_SECRET:
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RENDER"):
        raise RuntimeError("JWT_SECRET environment variable must be set in production")
    JWT_SECRET = "dev-secret-change-in-production"


# --------- FILE STORAGE CONFIGURATION ---------
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

COSTUMES_DIR = DATA_DIR / "costumes"
COSTUMES_DIR.mkdir(exist_ok=True)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
FRONTEND_DIR.mkdir(exist_ok=True)
