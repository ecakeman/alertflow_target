"""Shared fixtures.

The backend package lives under ``backend/`` so tests add it to sys.path rather
than requiring an editable install.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from fault_lab.config import load_settings  # noqa: E402
from fault_lab.main import create_app  # noqa: E402

CONTROL_TOKEN = "test-control-token"
DIAGNOSTICS_TOKEN = "test-diagnostics-token"


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "simulator.json"


@pytest.fixture
def settings(config_path: Path, tmp_path: Path):
    return load_settings(
        {
            "SIMULATOR_ADDR": ":8090",
            "SIMULATOR_CONFIG_PATH": str(config_path),
            "SIMULATOR_CONTROL_TOKEN": CONTROL_TOKEN,
            "SIMULATOR_DIAGNOSTICS_TOKEN": DIAGNOSTICS_TOKEN,
            "SIMULATOR_LOG_LEVEL": "warning",
            # Point at a path that does not exist so no static mount interferes.
            "SIMULATOR_FRONTEND_DIST": str(tmp_path / "no-dist"),
        }
    )


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def control_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {CONTROL_TOKEN}"}


@pytest.fixture
def diag_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {DIAGNOSTICS_TOKEN}"}


def make_state(*, health_mode="normal", slow_delay_ms=12000, diag_mode="normal", stale=900, items=None):
    return {
        "service": {"name": "Demo Order API", "version": "1.0.0"},
        "health": {"mode": health_mode, "slow_delay_ms": slow_delay_ms},
        "diagnostics": {"mode": diag_mode, "stale_by_seconds": stale, "items": items or []},
    }


def apply_state(client: TestClient, control_headers, **kwargs) -> dict:
    resp = client.put("/control/v1/state", json=make_state(**kwargs), headers=control_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# -- live server fixture (real TCP, for connection_reset verification) --------


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def live_server(settings):
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            httpx.get(base + "/healthz", timeout=0.5)
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.05)
    else:  # pragma: no cover - startup failure
        raise RuntimeError("live server did not start")

    try:
        yield base
    finally:
        server.should_exit = True
        thread.join(timeout=5)
