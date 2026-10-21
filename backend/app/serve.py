"""Production entry point: one service serving the API and the built frontend.

    uvicorn app.serve:app

The API is mounted under /api, which is the same path the Vite dev server
proxies, so the frontend code is identical in development and production.
Everything else is the React app; unknown paths get index.html so client-side
routes like /q/42 work on a full page load.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from .config import APP_ENV
from .main import app as api

DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def create_app(static_dir: Path) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/api", api)
    # Fail at startup in production if the frontend wasn't built into the
    # image; elsewhere (tests, CI) the build may legitimately not exist.
    check = APP_ENV == "production"
    app.mount("/", SPAStaticFiles(directory=static_dir, html=True, check_dir=check))
    return app


app = create_app(Path(os.environ.get("STATIC_DIR", DEFAULT_STATIC_DIR)))
