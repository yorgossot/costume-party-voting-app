from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from auth import get_current_user, require_admin

PROTECTED_JS_DIR = Path(__file__).parent.parent / "protected_js"

router = APIRouter()


@router.get("/js/api-auth.js", dependencies=[Depends(get_current_user)])
def serve_api_auth():
    return FileResponse(
        PROTECTED_JS_DIR / "api-auth.js", media_type="application/javascript"
    )


@router.get("/js/admin.js", dependencies=[Depends(require_admin)])
def serve_admin():
    return FileResponse(
        PROTECTED_JS_DIR / "admin.js", media_type="application/javascript"
    )
