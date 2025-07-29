from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, client, organizations, invites

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router, prefix="/v1/client", tags=["Authentication"])
app.include_router(client.router, prefix="/v1/client", tags=["Client"])
app.include_router(organizations.router, prefix="/v1/org", tags=["Organizations"])
app.include_router(invites.router, prefix="/v1/invite", tags=["Invites"])

# Отдельный роутер для валидации токенов (для Gateway)
from app.routers import auth as auth_validation
app.include_router(auth_validation.router, prefix="/v1/auth", tags=["Auth Validation"])


@app.get("/")
async def root():
    return {
        "message": "Authentication Service",
        "version": settings.app_version,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"} 