"""The read-only diagnostic evidence endpoint consumed by the Agent.

Returns a snapshot that satisfies the Agent diagnostics v1 contract, plus a few
deliberate modes (empty / unavailable / invalid / stale) so the Agent's handling
of insufficient, missing, malformed or outdated evidence can be exercised.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse

from .auth import check_token
from .schemas import DiagnosticItem, DiagnosticsMode, ItemKind, SimulatorState

router = APIRouter()

SCHEMA_VERSION = "v1"


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_item(item: DiagnosticItem, observed_at: datetime) -> dict:
    """Render one configured item into the v1 item shape.

    ``observed_at`` is already shifted for stale mode by the caller.
    """
    when = item.observed_at.astimezone(timezone.utc) if item.observed_at else observed_at
    payload: dict = {"kind": item.kind.value, "name": item.name, "observed_at": _rfc3339(when)}
    if item.kind in (ItemKind.component_health, ItemKind.dependency_health):
        payload["status"] = item.status.value if item.status else "unknown"
        payload["summary"] = item.summary or ""
    else:  # recent_error
        payload["summary"] = item.summary or ""
    if item.attributes:
        payload["attributes"] = dict(item.attributes)
    return payload


def build_snapshot(state: SimulatorState, now: datetime) -> dict:
    """Build the normal / empty / stale snapshot body (all contract-valid)."""
    diag = state.diagnostics
    shift = timedelta(seconds=diag.stale_by_seconds) if diag.mode == DiagnosticsMode.stale else timedelta(0)
    observed_at = now - shift

    items: list[dict] = []
    if diag.mode != DiagnosticsMode.empty:
        for item in diag.items:
            # Each item is shifted too so stale evidence is consistent.
            item_observed = (item.observed_at or now) - shift
            rendered = _render_item(item, observed_at)
            rendered["observed_at"] = _rfc3339(item_observed)
            items.append(rendered)

    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": _rfc3339(observed_at),
        "service": {"name": state.service.name, "version": state.service.version},
        "items": items,
    }


def build_invalid_snapshot(state: SimulatorState) -> dict:
    """A deliberately contract-violating body, for Agent input-validation tests."""
    return {
        "schema_version": "v0",
        # Intentionally missing "version".
        "service": {"name": state.service.name},
        "items": [
            # Unknown kind, illegal status, and no observed_at.
            {"kind": "not_a_real_kind", "name": "broken_evidence", "status": "mostly-fine"},
        ],
    }


@router.get("/diagnostics/v1/snapshot")
async def snapshot(
    request: Request,
    since: Optional[str] = Query(default=None, description="RFC3339 lower bound (contract compatibility only)"),
    until: Optional[str] = Query(default=None, description="RFC3339 upper bound (contract compatibility only)"),
    authorization: Optional[str] = Header(default=None),
):
    settings = request.app.state.settings
    check_token(authorization, settings.diagnostics_token, required=False)

    store = request.app.state.store
    state, _ = store.snapshot()
    mode = state.diagnostics.mode
    now = datetime.now(timezone.utc)

    if mode == DiagnosticsMode.unavailable:
        return JSONResponse(status_code=503, content={"error": "diagnostics temporarily unavailable"})

    if mode == DiagnosticsMode.invalid:
        return JSONResponse(status_code=200, content=build_invalid_snapshot(state))

    return JSONResponse(status_code=200, content=build_snapshot(state, now))
