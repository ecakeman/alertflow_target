"""Thread-safe state holder with atomic JSON persistence.

The store is the single source of truth for the current simulation. Requests
take an immutable snapshot at the start of their work, so a concurrent update
can never expose a half-written configuration to an in-flight request.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from .schemas import SimulatorState, default_state

logger = logging.getLogger("fault_lab.state")


class StateStore:
    def __init__(self, path: Path):
        self._path = Path(path)
        self._lock = threading.RLock()
        self._flap_lock = threading.Lock()
        self._flap_counter = 0
        self._state = default_state()
        self._updated_at = datetime.now(timezone.utc)
        self._load()

    # -- reads -------------------------------------------------------------

    def snapshot(self) -> tuple[SimulatorState, datetime]:
        """Return a deep copy of the state plus its last-updated timestamp."""
        with self._lock:
            return self._state.model_copy(deep=True), self._updated_at

    def next_flap(self) -> int:
        """Increment and return the per-request flap counter (1-based)."""
        with self._flap_lock:
            self._flap_counter += 1
            return self._flap_counter

    def flap_counter(self) -> int:
        with self._flap_lock:
            return self._flap_counter

    def reset_flap(self) -> None:
        with self._flap_lock:
            self._flap_counter = 0

    # -- writes ------------------------------------------------------------

    def update(self, new_state: SimulatorState) -> tuple[SimulatorState, datetime]:
        """Validate-then-apply. The caller validates; we persist before swap."""
        with self._lock:
            self._persist(new_state)
            self._state = new_state
            self._updated_at = datetime.now(timezone.utc)
            self.reset_flap()
            return self._state.model_copy(deep=True), self._updated_at

    def reset(self) -> tuple[SimulatorState, datetime]:
        return self.update(default_state())

    # -- persistence -------------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._state = SimulatorState.model_validate(raw)
        except Exception:  # noqa: BLE001 - a corrupt file must not stop boot
            logger.exception(
                "Could not load simulator config from %s; starting from defaults", self._path
            )

    def _persist(self, state: SimulatorState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2)
        # Write to a sibling temp file, flush+fsync, then atomically replace so
        # an interrupted write never leaves a half-written config behind.
        fd, tmp_name = tempfile.mkstemp(dir=str(self._path.parent), prefix=".simulator-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self._path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
