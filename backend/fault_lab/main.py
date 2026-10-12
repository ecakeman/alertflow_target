"""Application assembly and process entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import Settings, load_settings
from .routes_control import router as control_router
from .routes_diagnostics import router as diagnostics_router
from .routes_health import HealthEndpoint, router as health_router
from .routes_scenarios import router as scenarios_router
from .state_store import StateStore

MAX_BODY_BYTES = 128 * 1024


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _not_built_page() -> str:
    return """
<!doctype html>
<html lang="zh">
<head><meta charset="utf-8"><title>Fault Lab</title>
<style>body{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#0e151c;color:#dbe6ef;
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
main{max-width:640px;padding:40px;border:1px solid #24323f;border-radius:14px;background:#131d26}
code{color:#48c6d4}</style></head>
<body><main>
<h1>Fault Lab API 已启动</h1>
<p>前端静态资源尚未构建。请执行：</p>
<p><code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code></p>
<p>然后刷新本页。API 仍然可用：
<code>/health</code>、<code>/diagnostics/v1/snapshot</code>、<code>/control/v1/state</code>。</p>
</main></body></html>
"""


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()
    _configure_logging(settings.log_level)

    app = FastAPI(
        title="Fault Lab",
        version=__version__,
        description="HTTP Fault & Diagnostic Simulator",
    )
    app.state.settings = settings
    app.state.store = StateStore(settings.config_path)

    @app.middleware("http")
    async def limit_body_size(request: Request, call_next):  # noqa: ANN001
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"request body exceeds {MAX_BODY_BYTES} bytes"},
                    )
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "invalid content-length"})
        return await call_next(request)

    # Monitored target (raw ASGI so connection_reset is observable).
    app.add_route("/health", HealthEndpoint(app.state.store), methods=["GET"])
    app.include_router(health_router)
    app.include_router(diagnostics_router)
    app.include_router(control_router)
    app.include_router(scenarios_router)

    _mount_frontend(app, settings)
    return app


def _mount_frontend(app: FastAPI, settings: Settings) -> None:
    dist: Path = settings.frontend_dist  # type: ignore[assignment]
    index = dist / "index.html"
    if dist and dist.is_dir() and index.is_file():
        # Mounted last so API routes win; serves index.html for "/".
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
    else:
        @app.get("/", response_class=HTMLResponse)
        async def index_placeholder() -> str:
            return _not_built_page()


def main() -> None:
    import uvicorn

    settings = load_settings()
    if not settings.control_token:
        raise SystemExit(
            "SIMULATOR_CONTROL_TOKEN is required. Set it in the environment (see .env.example)."
        )
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
