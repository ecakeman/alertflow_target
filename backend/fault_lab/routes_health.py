"""The monitored target.

``GET /health`` is a raw ASGI endpoint so that every fault mode — including a
deliberately aborted connection — is produced in a way a real HTTP client can
observe. ``GET /healthz`` is the simulator's own liveness probe and never reacts
to the configured fault mode.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter
from starlette.responses import PlainTextResponse

from .state_store import StateStore

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness of the simulator process itself, independent of /health."""
    return {"status": "ok"}


class HealthEndpoint:
    """ASGI application implementing the configured /health behaviour."""

    def __init__(self, store: StateStore):
        self._store = store

    async def __call__(self, scope, receive, send) -> None:  # noqa: ANN001 - ASGI signature
        if scope.get("type") != "http":
            return

        state, _ = self._store.snapshot()
        mode = state.health.mode.value

        if mode == "normal":
            await self._text(send, 200, "ok\n")
            return

        if mode == "http_503":
            await self._text(send, 503, "service unavailable\n")
            return

        if mode == "slow":
            await asyncio.sleep(state.health.slow_delay_ms / 1000.0)
            await self._text(send, 200, "ok\n")
            return

        if mode == "flap":
            # Alternates per HTTP request: the 1st, 3rd, 5th ... request fails.
            seq = self._store.next_flap()
            if seq % 2 == 1:
                await self._text(send, 503, "service unavailable\n")
            else:
                await self._text(send, 200, "ok\n")
            return

        if mode == "connection_reset":
            await self._abort(send)
            return

        # Unknown mode cannot occur (validated), but respond safely just in case.
        await self._text(send, 200, "ok\n")

    @staticmethod
    async def _text(send, status_code: int, body: str) -> None:  # noqa: ANN001
        response = PlainTextResponse(body, status_code=status_code)
        await response({"type": "http"}, None, send)

    @staticmethod
    async def _abort(send) -> None:  # noqa: ANN001
        """Announce a body larger than we deliver, then drop the connection.

        The client sees the response headers, then the socket closes before the
        declared Content-Length is satisfied — i.e. a reset / interrupted
        response rather than a clean status code.
        """
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/plain; charset=utf-8"),
                    (b"content-length", b"1024"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b"partial response, connection reset", "more_body": True})
        # Raising here makes uvicorn tear the connection down mid-response.
        raise ConnectionResetError("simulated connection reset (connection_reset mode)")
