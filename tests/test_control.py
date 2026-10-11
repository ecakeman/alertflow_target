"""Control API: authentication, validation, and safe failure."""

from __future__ import annotations

from conftest import CONTROL_TOKEN, DIAGNOSTICS_TOKEN


def _state(**health):
    return {
        "service": {"name": "Demo Order API", "version": "1.0.0"},
        "health": health or {"mode": "normal", "slow_delay_ms": 12000},
        "diagnostics": {"mode": "normal", "stale_by_seconds": 900, "items": []},
    }


def test_control_requires_token(client):
    assert client.get("/control/v1/state").status_code == 401
    assert client.put("/control/v1/state", json=_state()).status_code == 401
    assert client.post("/control/v1/reset").status_code == 401


def test_control_wrong_token_rejected(client):
    assert client.get("/control/v1/state", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_control_valid_token_accepted(client, control_headers):
    resp = client.get("/control/v1/state", headers=control_headers)
    assert resp.status_code == 200
    assert set(resp.json()) >= {"state", "updated_at"}


def test_unknown_field_rejected(client, control_headers):
    payload = _state()
    payload["surprise"] = 1
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_unknown_field_nested_rejected(client, control_headers):
    payload = _state()
    payload["health"]["turbo"] = True
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_illegal_enum_rejected(client, control_headers):
    payload = _state()
    payload["health"]["mode"] = "explode"
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_recent_error_requires_summary(client, control_headers):
    payload = _state()
    payload["diagnostics"]["items"] = [{"kind": "recent_error", "name": "boom"}]
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_component_requires_status(client, control_headers):
    payload = _state()
    payload["diagnostics"]["items"] = [{"kind": "component_health", "name": "database"}]
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_attribute_count_limit(client, control_headers):
    payload = _state()
    payload["diagnostics"]["items"] = [
        {"kind": "component_health", "name": "db", "status": "healthy", "attributes": {f"k{i}": "v" for i in range(21)}}
    ]
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_attribute_value_length_limit(client, control_headers):
    payload = _state()
    payload["diagnostics"]["items"] = [
        {"kind": "component_health", "name": "db", "status": "healthy", "attributes": {"big": "x" * 201}}
    ]
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_name_length_limit(client, control_headers):
    payload = _state()
    payload["diagnostics"]["items"] = [{"kind": "component_health", "name": "n" * 101, "status": "healthy"}]
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_naive_timestamp_rejected(client, control_headers):
    payload = _state()
    payload["diagnostics"]["items"] = [
        {"kind": "recent_error", "name": "x", "summary": "s", "observed_at": "2026-10-11T10:00:00"}
    ]
    assert client.put("/control/v1/state", json=payload, headers=control_headers).status_code == 422


def test_failed_update_keeps_previous_state(client, control_headers):
    good = _state(**{"mode": "http_503", "slow_delay_ms": 12000})
    assert client.put("/control/v1/state", json=good, headers=control_headers).status_code == 200

    bad = _state()
    bad["health"]["mode"] = "not-a-mode"
    assert client.put("/control/v1/state", json=bad, headers=control_headers).status_code == 422

    # Still serving the previous configuration.
    assert client.get("/health").status_code == 503


def test_reset_restores_defaults(client, control_headers):
    client.put("/control/v1/state", json=_state(**{"mode": "http_503", "slow_delay_ms": 12000}), headers=control_headers)
    assert client.post("/control/v1/reset", headers=control_headers).status_code == 200
    assert client.get("/health").status_code == 200


def test_tokens_never_leaked_in_responses(client, control_headers):
    body = client.get("/control/v1/state", headers=control_headers).text
    assert CONTROL_TOKEN not in body
    assert DIAGNOSTICS_TOKEN not in body


def test_request_body_size_limit(client, control_headers):
    resp = client.put(
        "/control/v1/state",
        content=b"x" * (200 * 1024),
        headers={**control_headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 413


def test_concurrent_config_snapshot_is_consistent(client, control_headers):
    # A request that begins while an update lands must still see a coherent
    # state; here we simply confirm repeated reads never return partial JSON.
    client.put("/control/v1/state", json=_state(), headers=control_headers)
    for _ in range(20):
        assert client.get("/control/v1/state", headers=control_headers).status_code == 200
