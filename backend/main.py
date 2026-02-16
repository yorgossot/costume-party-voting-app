from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import COSTUMES_DIR, FRONTEND_DIR
from database import init_db
from generate_credentials import generate_users_from_access_codes
from auth import router as auth_router
from routers.costumes import router as costumes_router
from routers.voting import router as voting_router
from routers.users import router as users_router
from routers.admin import router as admin_router
from routers.protected_js import router as protected_js_router

app = FastAPI(title="Party Costume Voting")
init_db()
generate_users_from_access_codes()

app.mount("/static/costumes", StaticFiles(directory=str(COSTUMES_DIR)), name="costumes")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(costumes_router)
app.include_router(voting_router)
app.include_router(admin_router)
app.include_router(protected_js_router)

# Frontend catch-all (must be last)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
