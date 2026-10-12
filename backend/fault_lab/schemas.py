"""Pydantic models that define the simulator's configuration contract.

v2 adds first-class "internal state" evidence so the diagnostic Agent can reason
about *why* a service failed, not just *that* it failed:

* four new item kinds — ``resource``, ``saturation``, ``recent_change`` and
  ``slow_operation`` — alongside the original ``component_health``,
  ``dependency_health`` and ``recent_error``;
* a structured ``detail`` object on every item (kind-specific, JSON-shaped)
  in addition to the flat ``attributes`` bag kept for v1 compatibility;
* richer ``service`` metadata (env / instance / region / build);
* named ``profile`` archetypes that expand into a coherent, time-anchored set of
  internal-failure evidence (see ``profiles.py``).

Every control request is validated here before it is applied.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

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
MAX_DETAIL_KEYS = 24          # keys allowed per object level in `detail`
MAX_DETAIL_DEPTH = 3          # nesting depth of `detail`
MAX_DETAIL_VALUE = 400        # characters per scalar string in `detail`


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
    # v2 — internal state
    resource = "resource"
    saturation = "saturation"
    recent_change = "recent_change"
    slow_operation = "slow_operation"


# Kinds whose item must carry a status.
STATUS_KINDS = {ItemKind.component_health, ItemKind.dependency_health, ItemKind.resource}
# Kinds whose item must carry a non-empty summary.
SUMMARY_KINDS = {ItemKind.recent_error, ItemKind.recent_change, ItemKind.slow_operation}


class ItemStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"
    unknown = "unknown"


class HealthConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: HealthMode = HealthMode.normal
    slow_delay_ms: int = Field(default=SLOW_DELAY_DEFAULT_MS, ge=SLOW_DELAY_MIN_MS, le=SLOW_DELAY_MAX_MS)


def _check_detail(value: dict[str, Any]) -> dict[str, Any]:
    """Bound a kind-specific ``detail`` object: size, depth and scalar length.

    ``detail`` is intentionally schemaless per kind (documented in the v2
    contract), so validation enforces shape-safety rather than a fixed layout.
    """

    def walk(node: Any, depth: int) -> None:
        if depth > MAX_DETAIL_DEPTH:
            raise ValueError(f"detail nests deeper than {MAX_DETAIL_DEPTH} levels")
        if isinstance(node, dict):
            if len(node) > MAX_DETAIL_KEYS:
                raise ValueError(f"detail object holds more than {MAX_DETAIL_KEYS} keys")
            for key, item in node.items():
                if not isinstance(key, str) or len(key) > MAX_ATTRIBUTE_KEY:
                    raise ValueError(f"detail key is invalid or too long: {key!r}")
                walk(item, depth + 1)
        elif isinstance(node, list):
            if len(node) > MAX_DETAIL_KEYS:
                raise ValueError(f"detail list holds more than {MAX_DETAIL_KEYS} entries")
            for item in node:
                walk(item, depth + 1)
        elif isinstance(node, str):
            if len(node) > MAX_DETAIL_VALUE:
                raise ValueError(f"detail string exceeds {MAX_DETAIL_VALUE} characters")
        elif node is None or isinstance(node, (int, float, bool)):
            return
        else:
            raise ValueError(f"detail holds a non-JSON value: {type(node).__name__}")

    walk(value, 0)
    return value


class DiagnosticItem(BaseModel):
    """One diagnostic evidence item.

    ``observed_at`` is optional on input: when omitted the snapshot fills in the
    current time so the served payload always satisfies the Agent contract.
    """

    model_config = ConfigDict(extra="forbid")

    kind: ItemKind
    name: str = Field(min_length=1, max_length=MAX_NAME)
    status: Optional[ItemStatus] = None
    observed_at: Optional[datetime] = None
    summary: Optional[str] = Field(default=None, max_length=MAX_SUMMARY)
    # v2: structured, kind-specific internal state.
    detail: dict[str, Any] = Field(default_factory=dict)
    # v1 compatibility: flat string bag.
    attributes: dict[str, str] = Field(default_factory=dict)

    @field_validator("observed_at")
    @classmethod
    def _require_timezone(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("observed_at must be timezone-aware (RFC3339 with offset)")
        return value

    @field_validator("detail")
    @classmethod
    def _check_detail(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _check_detail(value)

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
        if self.kind in STATUS_KINDS and self.status is None:
            raise ValueError(f"status is required for {self.kind.value}")
        if self.kind in SUMMARY_KINDS and not self.summary:
            raise ValueError(f"summary is required for {self.kind.value}")
        return self


class DiagnosticsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: DiagnosticsMode = DiagnosticsMode.normal
    stale_by_seconds: int = Field(default=STALE_DEFAULT_SECONDS, ge=STALE_MIN_SECONDS, le=STALE_MAX_SECONDS)
    # v2: a named internal-failure archetype that expands into a coherent item
    # set (an explicit ``items`` list still wins when both are given).
    profile: Optional[str] = None
    items: list[DiagnosticItem] = Field(default_factory=list, max_length=MAX_ITEMS)

    @field_validator("profile")
    @classmethod
    def _known_profile(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        from .profiles import PROFILES  # local import keeps this module import-light

        if value not in PROFILES:
            raise ValueError(f"unknown profile: {value!r} (known: {', '.join(sorted(PROFILES))})")
        return value


class ServiceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Demo Order API", min_length=1, max_length=MAX_NAME)
    version: str = Field(default="1.0.0", min_length=1, max_length=50)
    env: str = Field(default="prod", min_length=1, max_length=32)
    instance: str = Field(default="order-api-1", min_length=1, max_length=64)
    region: str = Field(default="cn-north-1a", min_length=1, max_length=32)
    uptime_s: int = Field(default=86_400, ge=0)
    build: dict[str, str] = Field(default_factory=dict)


class SimulatorState(BaseModel):
    """The complete, atomically-applied simulator configuration."""

    model_config = ConfigDict(extra="forbid")

    service: ServiceInfo = Field(default_factory=ServiceInfo)
    health: HealthConfig = Field(default_factory=HealthConfig)
    diagnostics: DiagnosticsConfig = Field(default_factory=DiagnosticsConfig)


def default_state() -> SimulatorState:
    """A neutral, healthy baseline used on first boot and for resets."""
    return SimulatorState()
