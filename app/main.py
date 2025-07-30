from fastapi import FastAPI
from fastapi_jwt_auth import AuthJWT
from app.core.database import init_db
from app.api.auth.routes import router as auth_router
from app.core.config import settings
from fastapi.security import HTTPBearer

app = FastAPI(
    title="Student Management API",
    openapi_tags=[{"name": "auth", "description": "Authentication endpoints"}],
    openapi_extra={
        "security": [{"HTTPBearer": []}]
    }
)
security = HTTPBearer()
# Configure fastapi-jwt-auth
@AuthJWT.load_config
def get_config():
    return settings

app.include_router(auth_router, prefix="/api/auth")

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Student Management API"}