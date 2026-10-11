"""Persistence: survive restart, write atomically, tolerate a corrupt file."""

from __future__ import annotations

import glob
import json

from conftest import make_state
from fastapi.testclient import TestClient

from fault_lab.main import create_app


def test_state_survives_restart(settings, config_path, control_headers):
    app1 = create_app(settings)
    first = TestClient(app1)
    first.put("/control/v1/state", json=make_state(health_mode="http_503"), headers=control_headers)

    # A brand new process-level app reads the same file.
    app2 = create_app(settings)
    second = TestClient(app2)
    body = second.get("/control/v1/state", headers=control_headers).json()
    assert body["state"]["health"]["mode"] == "http_503"
    assert second.get("/health").status_code == 503
    assert config_path.exists()


def test_atomic_write_leaves_no_temp_files(settings, config_path, control_headers):
    app = create_app(settings)
    client = TestClient(app)
    client.put("/control/v1/state", json=make_state(health_mode="slow", slow_delay_ms=100), headers=control_headers)

    leftovers = glob.glob(str(config_path.parent / ".simulator-*.tmp"))
    assert leftovers == []

    # The persisted file is complete, valid JSON matching the applied state.
    on_disk = json.loads(config_path.read_text(encoding="utf-8"))
    assert on_disk["health"]["mode"] == "slow"
    assert on_disk["health"]["slow_delay_ms"] == 100


def test_corrupt_config_falls_back_to_defaults(settings, config_path, control_headers):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{ this is not json", encoding="utf-8")

    app = create_app(settings)  # must not raise
    client = TestClient(app)
    body = client.get("/control/v1/state", headers=control_headers).json()
    assert body["state"]["health"]["mode"] == "normal"
    assert client.get("/health").status_code == 200


def test_default_config_written_on_first_update(settings, config_path):
    assert not config_path.exists()
    app = create_app(settings)
    assert not config_path.exists()  # boot alone does not write
    TestClient(app).post("/control/v1/reset", headers={"Authorization": "Bearer test-control-token"})
    assert config_path.exists()
