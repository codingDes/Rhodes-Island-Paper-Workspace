from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_lore import router as lore_router
from app.api.routes_operator import router as operator_router
from app.api.routes_chat import router as chat_router
from app.api.routes_summary import router as summary_router
from app.api.routes_upload import router as upload_router
from app.api.routes_archive_state import router as archive_state_router
from app.config import Settings


def create_app() -> FastAPI:
    settings = Settings.load()

    app = FastAPI(title=settings.app_name)

    allow_origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure expected data directories exist (Step1: just create folders, no DB yet).
    for p in (settings.data_dir, settings.docs_dir, settings.index_dir, settings.memory_dir):
        Path(p).mkdir(parents=True, exist_ok=True)
    Path(settings.data_dir / "lore" / "operators").mkdir(parents=True, exist_ok=True)

    app.include_router(upload_router)
    app.include_router(summary_router)
    app.include_router(chat_router)
    app.include_router(operator_router)
    app.include_router(lore_router)
    app.include_router(archive_state_router)

    @app.get("/api/health")
    def health():
        return {"ok": True, "app": settings.app_name}

    web_dir = Path("web")
    if web_dir.exists():
        app.mount("/assets", StaticFiles(directory="web"), name="assets")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(web_dir / "index.html")

    return app


app = create_app()

