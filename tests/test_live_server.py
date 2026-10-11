"""Real-socket verification.

The in-process TestClient cannot faithfully reproduce an aborted connection, so
this module runs an actual uvicorn server and drives it with a real HTTP client.
This is the evidence that ``connection_reset`` behaves as a genuine client would
experience it.
"""

from __future__ import annotations

import httpx
import pytest
from conftest import make_state


def _apply(base, control_headers, **kwargs):
    resp = httpx.put(base + "/control/v1/state", json=make_state(**kwargs), headers=control_headers, timeout=5)
    assert resp.status_code == 200, resp.text


def test_live_normal_and_503(live_server, control_headers):
    _apply(live_server, control_headers, health_mode="normal")
    assert httpx.get(live_server + "/health", timeout=5).status_code == 200
    _apply(live_server, control_headers, health_mode="http_503")
    assert httpx.get(live_server + "/health", timeout=5).status_code == 503


def test_live_flap_alternates(live_server, control_headers):
    _apply(live_server, control_headers, health_mode="flap")
    codes = [httpx.get(live_server + "/health", timeout=5).status_code for _ in range(4)]
    assert codes == [503, 200, 503, 200]


def test_live_connection_reset_aborts(live_server, control_headers):
    assert httpx.get(live_server + "/health", timeout=5).status_code == 200
    _apply(live_server, control_headers, health_mode="connection_reset")

    # A real HTTP client must see the response fail, not a clean 200.
    with pytest.raises(httpx.HTTPError):
        httpx.get(live_server + "/health", timeout=5)

    # The simulator itself remains alive and controllable.
    assert httpx.get(live_server + "/healthz", timeout=5).status_code == 200
