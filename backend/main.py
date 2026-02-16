from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps

from config import COSTUMES_DIR, FRONTEND_DIR, THUMB_WIDTH, THUMB_QUALITY
from database import init_db
from generate_credentials import generate_users_from_access_codes
from auth import router as auth_router
from routers.costumes import router as costumes_router
from routers.voting import router as voting_router
from routers.users import router as users_router
from routers.admin import router as admin_router
from routers.protected_js import router as protected_js_router


def generate_missing_thumbnails():
    for img_file in COSTUMES_DIR.glob("*.jpg"):
        if img_file.name.startswith("thumb_"):
            continue
        thumb_path = img_file.parent / f"thumb_{img_file.name}"
        if not thumb_path.exists():
            try:
                img = Image.open(img_file)
                img = ImageOps.exif_transpose(img)
                if img.width > THUMB_WIDTH:
                    ratio = THUMB_WIDTH / img.width
                    img = img.resize(
                        (THUMB_WIDTH, int(img.height * ratio)), Image.LANCZOS
                    )
                img = img.convert("RGB")
                img.save(thumb_path, "JPEG", quality=THUMB_QUALITY)
                print(f"Generated thumbnail: {thumb_path.name}")
            except Exception as e:
                print(f"Error generating thumbnail for {img_file.name}: {e}")


app = FastAPI(title="Party Costume Voting")
init_db()
generate_users_from_access_codes()
generate_missing_thumbnails()

app.mount("/static/costumes", StaticFiles(directory=str(COSTUMES_DIR)), name="costumes")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(costumes_router)
app.include_router(voting_router)
app.include_router(admin_router)
app.include_router(protected_js_router)

# Frontend catch-all (must be last)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
