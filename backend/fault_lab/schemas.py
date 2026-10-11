"""Pydantic models that define the simulator's configuration contract.

Every control request is validated against these models before it is applied,
and unknown fields / illegal enum values / over-long text are rejected here so
the store never holds a half-valid configuration.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Bounds shared with the frontend so both sides agree on the limits.
SLOW_DELAY_MIN_MS = 0
SLOW_DELAY_MAX_MS = 60_000
SLOW_DELAY_DEFAULT_MS = 12_000
STALE_MIN_SECONDS = 0
STALE_MAX_SECONDS = 86_400
STALE_DEFAULT_SECONDS = 900
MAX_ITEMS = 100
MAX_ATTRIBUTES = 20
MAX_ATTRIBUTE_KEY = 64
MAX_ATTRIBUTE_VALUE = 200
MAX_NAME = 100
MAX_SUMMARY = 500


class HealthMode(str, Enum):
    normal = "normal"
    http_503 = "http_503"
    slow = "slow"
    flap = "flap"
    connection_reset = "connection_reset"


class DiagnosticsMode(str, Enum):
    normal = "normal"
    empty = "empty"
    unavailable = "unavailable"
    invalid = "invalid"
    stale = "stale"


class ItemKind(str, Enum):
    component_health = "component_health"
    dependency_health = "dependency_health"
    recent_error = "recent_error"


class ItemStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"
    unknown = "unknown"


class HealthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: HealthMode = HealthMode.normal
    slow_delay_ms: int = Field(default=SLOW_DELAY_DEFAULT_MS, ge=SLOW_DELAY_MIN_MS, le=SLOW_DELAY_MAX_MS)


class DiagnosticItem(BaseModel):
    """One diagnostic evidence item.

    ``observed_at`` is optional on input: when omitted the snapshot fills in the
    current time so the served payload always satisfies the Agent v1 contract.
    """

    model_config = ConfigDict(extra="forbid")

    kind: ItemKind
    name: str = Field(min_length=1, max_length=MAX_NAME)
    status: Optional[ItemStatus] = None
    observed_at: Optional[datetime] = None
    summary: Optional[str] = Field(default=None, max_length=MAX_SUMMARY)
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("observed_at")
    @classmethod
    def _require_timezone(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("observed_at must be timezone-aware (RFC3339 with offset)")
        return value

    @field_validator("attributes")
    @classmethod
    def _check_attributes(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > MAX_ATTRIBUTES:
            raise ValueError(f"attributes may hold at most {MAX_ATTRIBUTES} keys")
        clean: dict[str, str] = {}
        for key, raw in value.items():
            if len(key) > MAX_ATTRIBUTE_KEY:
                raise ValueError(f"attribute key exceeds {MAX_ATTRIBUTE_KEY} characters: {key!r}")
            text = raw if isinstance(raw, str) else str(raw)
            if len(text) > MAX_ATTRIBUTE_VALUE:
                raise ValueError(f"attribute value for {key!r} exceeds {MAX_ATTRIBUTE_VALUE} characters")
            clean[key] = text
        return clean

    @field_validator("summary")
    @classmethod
    def _blank_summary_is_none(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value.strip() == "":
            return None
        return value

    @model_validator(mode="after")
    def _required_fields_for_kind(self) -> "DiagnosticItem":
        if self.kind in (ItemKind.component_health, ItemKind.dependency_health):
            if self.status is None:
                raise ValueError(f"status is required for {self.kind.value}")
        if self.kind == ItemKind.recent_error and not self.summary:
            raise ValueError("summary is required for recent_error")
        return self


class DiagnosticsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: DiagnosticsMode = DiagnosticsMode.normal
    stale_by_seconds: int = Field(default=STALE_DEFAULT_SECONDS, ge=STALE_MIN_SECONDS, le=STALE_MAX_SECONDS)
    items: list[DiagnosticItem] = Field(default_factory=list, max_length=MAX_ITEMS)


class ServiceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Demo Order API", min_length=1, max_length=MAX_NAME)
    version: str = Field(default="1.0.0", min_length=1, max_length=50)


class SimulatorState(BaseModel):
    """The complete, atomically-applied simulator configuration."""

    model_config = ConfigDict(extra="forbid")

    service: ServiceInfo = Field(default_factory=ServiceInfo)
    health: HealthConfig = Field(default_factory=HealthConfig)
    diagnostics: DiagnosticsConfig = Field(default_factory=DiagnosticsConfig)


def default_state() -> SimulatorState:
    """A neutral, healthy baseline used on first boot and for resets."""
    return SimulatorState()
