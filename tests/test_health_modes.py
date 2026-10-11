"""Every health mode must produce its documented HTTP behaviour."""

from __future__ import annotations

import time

import pytest
from conftest import apply_state


def test_normal_returns_200(client, control_headers):
    apply_state(client, control_headers, health_mode="normal")
    resp = client.get("/health")
    assert resp.status_code == 200


def test_http_503_returns_503_every_time(client, control_headers):
    apply_state(client, control_headers, health_mode="http_503")
    assert client.get("/health").status_code == 503
    assert client.get("/health").status_code == 503


def test_slow_delays_then_returns_200(client, control_headers):
    apply_state(client, control_headers, health_mode="slow", slow_delay_ms=200)
    started = time.monotonic()
    resp = client.get("/health")
    elapsed = time.monotonic() - started
    assert resp.status_code == 200
    assert elapsed >= 0.18


def test_flap_alternates_per_request_and_resets(client, control_headers):
    apply_state(client, control_headers, health_mode="flap")
    codes = [client.get("/health").status_code for _ in range(4)]
    assert codes == [503, 200, 503, 200]

    # Applying a configuration resets the sequence.
    apply_state(client, control_headers, health_mode="flap")
    assert client.get("/health").status_code == 503

    # A full reset restores the default (normal) configuration...
    assert client.post("/control/v1/reset", headers=control_headers).status_code == 200
    assert client.get("/health").status_code == 200
    # ...and clears the flap sequence, so the next flap starts at 503 again.
    apply_state(client, control_headers, health_mode="flap")
    assert client.get("/health").status_code == 503


def test_healthz_is_independent_of_fault_mode(client, control_headers):
    apply_state(client, control_headers, health_mode="http_503")
    assert client.get("/health").status_code == 503
    liveness = client.get("/healthz")
    assert liveness.status_code == 200
    assert liveness.json() == {"status": "ok"}


def test_flap_counter_reported_in_state(client, control_headers):
    apply_state(client, control_headers, health_mode="flap")
    client.get("/health")
    client.get("/health")
    state = client.get("/control/v1/state", headers=control_headers).json()
    assert state["flap_counter"] == 2


@pytest.mark.parametrize("delay", [-1, 60001, "fast"])
def test_slow_delay_out_of_range_rejected(client, control_headers, delay):
    resp = client.put(
        "/control/v1/state",
        json={
            "service": {"name": "Demo", "version": "1.0.0"},
            "health": {"mode": "slow", "slow_delay_ms": delay},
            "diagnostics": {"mode": "normal", "stale_by_seconds": 900, "items": []},
        },
        headers=control_headers,
    )
    assert resp.status_code == 422
