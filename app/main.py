from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from sqlalchemy import text
from app.core.database import AsyncSessionFactory
from app.routers.appointments import router as appointments_router

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)

app.include_router(appointments_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Patient Intake API",
        "environment": settings.app_env,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }

@app.get("/database-health")
async def database_health() -> dict[str, str]:
    async with AsyncSessionFactory() as session:
        await session.execute(text("SELECT 1"))

    return {
        "database": "connected",
    }