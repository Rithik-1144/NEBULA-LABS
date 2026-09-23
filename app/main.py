from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.telegram_routes import router as telegram_router
from app.api.dashboard_routes import router as dashboard_router
from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.telegram.telegram_app import setup_telegram_app

configure_logging()
settings = get_settings()

app = FastAPI(title='Nebula KnowLab Supermarket Ops Agent', version='0.1.0')
app.include_router(health_router)
app.include_router(telegram_router)
app.include_router(dashboard_router)
design_dir = Path(__file__).resolve().parent / 'design'
app.mount('/ui/assets', StaticFiles(directory=design_dir), name='ui-assets')
setup_telegram_app(app)


@app.get('/')
def root() -> FileResponse:
    return FileResponse(design_dir / 'index.html')
