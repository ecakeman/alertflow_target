"""Console-only management API.

Everything under ``/control/v1`` requires the independent control bearer token.
The control token is never echoed back, never appears in the diagnostics
snapshot, and is not the same credential the Agent uses.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from .auth import check_token
from .schemas import SimulatorState

router = APIRouter(prefix="/control/v1")


def require_control_token(request: Request, authorization: Optional[str] = Header(default=None)) -> None:
    settings = request.app.state.settings
    check_token(authorization, settings.control_token, required=True)


def _state_response(state: SimulatorState, updated_at) -> dict:
    return {
        "state": state.model_dump(mode="json"),
        "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
        "flap_counter": None,  # filled by caller where relevant
    }


@router.get("/state", dependencies=[Depends(require_control_token)])
async def get_state(request: Request) -> JSONResponse:
    state, updated_at = request.app.state.store.snapshot()
    payload = _state_response(state, updated_at)
    payload["flap_counter"] = request.app.state.store.flap_counter()
    return JSONResponse(content=payload)


@router.put("/state", dependencies=[Depends(require_control_token)])
async def put_state(request: Request, body: SimulatorState) -> JSONResponse:
    # FastAPI has already validated ``body`` against the strict schema; unknown
    # fields, illegal enums and over-long text are rejected with a 422 before we
    # ever reach here, so the previous configuration is left untouched.
    state, updated_at = request.app.state.store.update(body)
    payload = _state_response(state, updated_at)
    payload["flap_counter"] = request.app.state.store.flap_counter()
    return JSONResponse(content=payload)


@router.post("/reset", dependencies=[Depends(require_control_token)])
async def reset(request: Request) -> JSONResponse:
    state, updated_at = request.app.state.store.reset()
    payload = _state_response(state, updated_at)
    payload["flap_counter"] = 0
    return JSONResponse(content=payload)
