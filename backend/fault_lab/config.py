"""Runtime configuration, sourced entirely from environment variables.

Nothing here is hard-coded into business logic: the listen address, the config
file path and both credentials are read from the environment so the same image
can be deployed anywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ADDR = ":8090"
DEFAULT_CONFIG_PATH = "./config/simulator.json"


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the process configuration."""

    addr: str
    config_path: Path
    control_token: str
    diagnostics_token: str | None
    log_level: str
    frontend_dist: Path | None

    @property
    def host(self) -> str:
        if self.addr.startswith(":"):
            return "0.0.0.0"
        return self.addr.rsplit(":", 1)[0]

    @property
    def port(self) -> int:
        return int(self.addr.rsplit(":", 1)[-1])


def load_settings(env: dict[str, str] | None = None) -> Settings:
    env = env if env is not None else os.environ

    addr = env.get("SIMULATOR_ADDR", DEFAULT_ADDR)
    config_path = Path(env.get("SIMULATOR_CONFIG_PATH", DEFAULT_CONFIG_PATH))
    control_token = env.get("SIMULATOR_CONTROL_TOKEN", "")
    diagnostics_token = env.get("SIMULATOR_DIAGNOSTICS_TOKEN") or None
    log_level = env.get("SIMULATOR_LOG_LEVEL", "info").lower()

    frontend_env = env.get("SIMULATOR_FRONTEND_DIST")
    # Default: <project root>/frontend/dist, resolved relative to this file.
    default_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    frontend_dist = Path(frontend_env) if frontend_env else default_dist

    return Settings(
        addr=addr,
        config_path=config_path,
        control_token=control_token,
        diagnostics_token=diagnostics_token,
        log_level=log_level,
        frontend_dist=frontend_dist,
    )
