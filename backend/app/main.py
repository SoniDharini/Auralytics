from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.db.seed import seed_database


from app.db.migrate import auto_migrate_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Ensure all latest model columns exist
    await auto_migrate_db(engine)
    # Seed initial development demo data if empty
    await seed_database()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Influencer Marketing SaaS API — From Discovery to ROI",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# CORS Middleware — preflight OPTIONS must succeed for login/register/refresh.
_cors_kwargs: dict = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
if settings.ENVIRONMENT == "development":
    # Allow any localhost / 127.0.0.1 port (Vite may use 5174, etc.).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        **_cors_kwargs,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        **_cors_kwargs,
    )


@app.get("/health", tags=["Health"], summary="System health status check")
async def health_check():
    return {
        "status": "ok",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Mount versioned API routes
app.include_router(api_router, prefix="/api/v1")

_SPA_DIR = Path(__file__).resolve().parents[1] / "spa_dist"


def _mount_spa() -> None:
    """Serve the production frontend from spa_dist when it is present."""
    if not _SPA_DIR.is_dir() or not (_SPA_DIR / "index.html").is_file():
        return

    assets_dir = _SPA_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        reserved = {"api", "health", "docs", "redoc", "openapi.json"}
        first = full_path.split("/", 1)[0]
        if first in reserved:
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (_SPA_DIR / full_path).resolve()
        try:
            candidate.relative_to(_SPA_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Not Found")
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_SPA_DIR / "index.html")


_mount_spa()
