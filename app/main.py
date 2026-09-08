from functools import lru_cache
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionFactory, get_db
from app.routers.appointments import router as appointments_router
from app.routers.intake import router as intake_router
from app.routers.records import router as records_router


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
)

app.include_router(appointments_router)
app.include_router(intake_router)
app.include_router(records_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, 
                   settings.professional_frontend_url,],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache
def _get_expected_alembic_heads() -> frozenset[str]:
    """Return the schema revisions shipped with this application image."""
    project_root = Path(__file__).resolve().parent.parent
    alembic_config = Config(str(project_root / "alembic.ini"))
    scripts = ScriptDirectory.from_config(alembic_config)
    return frozenset(scripts.get_heads())


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


@app.get("/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Check both database connectivity and the deployed Alembic schema."""
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": "unavailable",
                "schema": "unknown",
            },
        ) from exc

    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        current_heads = frozenset(result.scalars().all())
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": "connected",
                "schema": "unavailable",
            },
        ) from exc

    if current_heads != _get_expected_alembic_heads():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "database": "connected",
                "schema": "out_of_date",
            },
        )

    return {
        "status": "ready",
        "database": "connected",
        "schema": "current",
    }


@app.get("/database-health")
async def database_health() -> dict[str, str]:
    async with AsyncSessionFactory() as session:
        await session.execute(text("SELECT 1"))

    return {
        "database": "connected",
    }
