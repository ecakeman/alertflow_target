"""Diagnostic snapshot modes and their contract compliance."""

from __future__ import annotations

from datetime import datetime, timezone

from conftest import apply_state, make_state

COMPONENT = {
    "kind": "component_health",
    "name": "database",
    "status": "degraded",
    "summary": "Connection pool is close to its limit",
    "attributes": {"pool_usage": "92%"},
}
DEPENDENCY = {
    "kind": "dependency_health",
    "name": "payment_provider",
    "status": "healthy",
    "summary": "Recent dependency checks succeeded",
}
ERROR = {
    "kind": "recent_error",
    "name": "database_timeout",
    "summary": "Query exceeded the configured timeout",
}


def _snapshot(client, diag_headers):
    return client.get("/diagnostics/v1/snapshot", headers=diag_headers)


def test_normal_snapshot_shape(client, control_headers, diag_headers):
    apply_state(client, control_headers, items=[COMPONENT, DEPENDENCY, ERROR])
    body = _snapshot(client, diag_headers).json()
    assert body["schema_version"] == "v2"
    assert body["service"]["name"] == "Demo Order API"
    assert body["service"]["version"] == "1.0.0"
    # v2 adds richer service metadata.
    for key in ("env", "instance", "region", "uptime_s"):
        assert key in body["service"]
    kinds = [item["kind"] for item in body["items"]]
    assert kinds == ["component_health", "dependency_health", "recent_error"]
    for item in body["items"]:
        assert "observed_at" in item and item["observed_at"].endswith("Z")
    assert body["items"][0]["status"] == "degraded"
    assert body["items"][0]["attributes"] == {"pool_usage": "92%"}
    # recent_error carries no status field.
    assert "status" not in body["items"][2]


def test_empty_mode_returns_valid_but_empty(client, control_headers, diag_headers):
    apply_state(client, control_headers, diag_mode="empty", items=[COMPONENT])
    resp = _snapshot(client, diag_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema_version"] == "v2"
    assert body["items"] == []


def test_unavailable_mode_returns_non_2xx(client, control_headers, diag_headers):
    apply_state(client, control_headers, diag_mode="unavailable")
    resp = _snapshot(client, diag_headers)
    assert resp.status_code >= 400


def test_invalid_mode_violates_contract(client, control_headers, diag_headers):
    apply_state(client, control_headers, diag_mode="invalid")
    body = _snapshot(client, diag_headers).json()
    assert body["schema_version"] != "v2"
    assert "version" not in body["service"]
    assert body["items"][0]["kind"] not in {"component_health", "dependency_health", "recent_error"}
    assert "observed_at" not in body["items"][0]


def test_stale_mode_rolls_back_observed_at(client, control_headers, diag_headers):
    apply_state(client, control_headers, diag_mode="stale", stale=3600, items=[COMPONENT])
    body = _snapshot(client, diag_headers).json()
    observed = datetime.strptime(body["observed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - observed
    assert age.total_seconds() >= 3500


def test_missing_evidence_is_not_invented(client, control_headers, diag_headers):
    # Only one component is configured; nothing is fabricated for the others.
    apply_state(client, control_headers, items=[COMPONENT])
    body = _snapshot(client, diag_headers).json()
    assert len(body["items"]) == 1


def test_diagnostics_token_optional_but_enforced_when_set(client, control_headers):
    apply_state(client, control_headers)
    assert client.get("/diagnostics/v1/snapshot").status_code == 401
    assert client.get("/diagnostics/v1/snapshot", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert (
        client.get("/diagnostics/v1/snapshot", headers={"Authorization": "Bearer test-diagnostics-token"}).status_code
        == 200
    )


def test_since_until_accepted(client, diag_headers):
    resp = client.get(
        "/diagnostics/v1/snapshot?since=2026-10-11T00:00:00Z&until=2026-10-11T23:59:59Z",
        headers=diag_headers,
    )
    assert resp.status_code == 200


# -- v2: internal state, profiles and structured detail ----------------------


def test_profile_expands_to_internal_evidence(client, control_headers, diag_headers):
    apply_state(client, control_headers, profile="db_pool_exhaustion")
    body = _snapshot(client, diag_headers).json()
    assert body["schema_version"] == "v2"
    kinds = {item["kind"] for item in body["items"]}
    assert {"component_health", "dependency_health", "recent_error", "saturation", "resource"} <= kinds
    # The evidence tells a timeline: the dependency degrades before errors appear.
    by_kind = {item["kind"]: item["observed_at"] for item in body["items"]}
    assert by_kind["dependency_health"] < by_kind["recent_error"]
    # Structured detail rides along.
    pool = next(i for i in body["items"] if i["name"] == "db_connection_pool" and i["kind"] == "component_health")
    assert pool["detail"]["pool"]["waiting"] > 0
    assert pool["status"] == "unhealthy"


def test_unknown_profile_rejected(client, control_headers):
    payload = make_state(profile="does_not_exist")
    resp = client.put("/control/v1/state", json=payload, headers=control_headers)
    assert resp.status_code == 422


def test_detail_bounds_are_enforced(client, control_headers):
    payload = make_state(
        items=[{"kind": "component_health", "name": "db", "status": "healthy", "detail": {"big": "x" * 401}}]
    )
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422

    payload = make_state(
        items=[{"kind": "component_health", "name": "db", "status": "healthy",
                "detail": {f"k{i}": "v" for i in range(25)}}]
    )
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422
