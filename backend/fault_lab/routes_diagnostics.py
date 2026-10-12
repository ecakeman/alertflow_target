"""The read-only diagnostic evidence endpoint consumed by the Agent.

Serves the v2 diagnostic contract: rich, structured *internal state* evidence —
component / dependency health, raised errors, resource and saturation pressure,
recent changes and slow operations — so the Agent can reason about the cause of
a failure, not merely restate it.

Deliberate modes (empty / unavailable / invalid / stale) remain so the Agent's
handling of insufficient, missing, malformed or outdated evidence is exercised.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse

from .auth import check_token
from .profiles import PROFILES
from .schemas import DiagnosticItem, DiagnosticsMode, SimulatorState

router = APIRouter()

SCHEMA_VERSION = "v2"


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_item(item: DiagnosticItem, observed_at: datetime) -> dict:
    """Render one configured item into the v2 item shape."""
    when = item.observed_at.astimezone(timezone.utc) if item.observed_at else observed_at
    payload: dict = {"kind": item.kind.value, "name": item.name, "observed_at": _rfc3339(when)}
    if item.status is not None:
        payload["status"] = item.status.value
    if item.summary:
        payload["summary"] = item.summary
    if item.detail:
        payload["detail"] = dict(item.detail)
    if item.attributes:
        payload["attributes"] = dict(item.attributes)
    return payload


def _render_profile_item(raw: dict, now: datetime, shift: timedelta) -> dict:
    """Render one profile-generated item; its epoch is ``now + offset - shift``."""
    observed = now + timedelta(seconds=int(raw.get("_offset", 0))) - shift
    payload: dict = {"kind": raw["kind"], "name": raw["name"], "observed_at": _rfc3339(observed)}
    if raw.get("status"):
        payload["status"] = raw["status"]
    if raw.get("summary"):
        payload["summary"] = raw["summary"]
    if raw.get("detail"):
        payload["detail"] = dict(raw["detail"])
    if raw.get("attributes"):
        payload["attributes"] = dict(raw["attributes"])
    return payload


def _service_block(state: SimulatorState) -> dict:
    svc = state.service
    block: dict = {
        "name": svc.name,
        "version": svc.version,
        "env": svc.env,
        "instance": svc.instance,
        "region": svc.region,
        "uptime_s": svc.uptime_s,
    }
    if svc.build:
        block["build"] = dict(svc.build)
    return block


def build_snapshot(state: SimulatorState, now: datetime) -> dict:
    """Build the normal / empty / stale snapshot body (all contract-valid)."""
    diag = state.diagnostics
    shift = timedelta(seconds=diag.stale_by_seconds) if diag.mode == DiagnosticsMode.stale else timedelta(0)
    observed_at = now - shift

    items: list[dict] = []
    if diag.mode != DiagnosticsMode.empty:
        if diag.items:
            for item in diag.items:
                item_observed = (item.observed_at or now) - shift
                rendered = _render_item(item, observed_at)
                rendered["observed_at"] = _rfc3339(item_observed)
                items.append(rendered)
        elif diag.profile:
            items = [_render_profile_item(raw, now, shift) for raw in PROFILES[diag.profile](now)]

    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": _rfc3339(observed_at),
        "service": _service_block(state),
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
