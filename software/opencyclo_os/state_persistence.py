"""
OpenCyclo OS — State Persistence & Recovery
=============================================

Handles saving and restoring the reactor state after power loss.

Design:
  - Writes state to a JSON file every state transition and every N seconds
  - On startup, checks for a saved state file and resumes from it
  - Keeps a rolling history for audit trail

Spec reference: TODO.md Phase 3.1 (State transition logic and persistence)
"""

import json
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import OperatingState


STATE_FILE = Path("/var/log/opencyclo/reactor_state.json")
HISTORY_FILE = Path("/var/log/opencyclo/state_history.jsonl")

# Fallback for Windows / dev environments
if sys.platform == "win32":
    STATE_FILE = Path(__file__).resolve().parent / "state_data" / "reactor_state.json"
    HISTORY_FILE = Path(__file__).resolve().parent / "state_data" / "state_history.jsonl"


class StatePersistence:
    """
    Save and restore reactor operating state across power cycles.
    """

    def __init__(self, state_file: Optional[Path] = None, history_file: Optional[Path] = None):
        self.state_file = state_file or STATE_FILE
        self.history_file = history_file or HISTORY_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        state: OperatingState,
        nursery_start: Optional[float] = None,
        metrics: Optional[dict] = None,
    ) -> None:
        """
        Persist the current state to disk.

        Args:
            state: Current operating state
            nursery_start: Timestamp when nursery mode started (if applicable)
            metrics: Latest telemetry metrics snapshot
        """
        data = {
            "state": state.name,
            "nursery_start": nursery_start,
            "metrics": metrics or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_ts": time.time(),
        }

        # Atomic-ish write: write to .tmp then rename
        tmp_file = self.state_file.with_suffix(".tmp")
        with open(tmp_file, "w") as f:
            json.dump(data, f, indent=2)
        tmp_file.replace(self.state_file)

        # Append to history (audit trail)
        with open(self.history_file, "a") as f:
            f.write(json.dumps(data) + "\n")

    def load(self) -> Optional[dict]:
        """
        Load the last saved state from disk.

        Returns:
            Dict with state data, or None if no saved state exists.
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            # Validate the state string
            state_name = data.get("state", "IDLE")
            try:
                OperatingState[state_name]
            except KeyError:
                return None

            return data

        except (json.JSONDecodeError, IOError):
            return None

    def get_recovery_state(self) -> OperatingState:
        """
        Determine the appropriate state to recover into.

        Recovery logic:
          - If saved state is IDLE → start fresh (IDLE)
          - If saved state is NURSERY → check if 48h timer should have elapsed
            - If yes → skip to LOGARITHMIC_GROWTH
            - If no → resume NURSERY with remaining time
          - If saved state is LOGARITHMIC_GROWTH → resume LOGARITHMIC_GROWTH
          - If saved state is STEADY_STATE_TURBIDOSTAT → resume it
        """
        data = self.load()
        if data is None:
            return OperatingState.IDLE

        state_name = data.get("state", "IDLE")
        state = OperatingState[state_name]

        if state == OperatingState.NURSERY:
            nursery_start = data.get("nursery_start")
            if nursery_start is not None:
                elapsed = time.time() - nursery_start
                nursery_duration = 48 * 3600  # 48 hours
                if elapsed >= nursery_duration:
                    # Nursery period would have completed during downtime
                    return OperatingState.LOGARITHMIC_GROWTH
            # Otherwise resume nursery with remaining time
            return OperatingState.NURSERY

        return state

    def get_nursery_remaining(self) -> float:
        """
        Returns remaining nursery time in seconds, or 0 if nursery is complete.
        """
        data = self.load()
        if data is None:
            return 48 * 3600  # Full nursery period

        nursery_start = data.get("nursery_start")
        if nursery_start is None:
            return 48 * 3600

        elapsed = time.time() - nursery_start
        remaining = (48 * 3600) - elapsed
        return max(0.0, remaining)

    def clear(self) -> None:
        """Delete the saved state (for clean restart)."""
        if self.state_file.exists():
            self.state_file.unlink()


if __name__ == "__main__":
    # Quick test
    sp = StatePersistence()
    print(f"State file: {sp.state_file}")

    # Save a test state
    sp.save(OperatingState.NURSERY, nursery_start=time.time())
    print(f"Saved NURSERY state")

    # Load it back
    data = sp.load()
    print(f"Loaded: {data}")

    # Check recovery
    recovery = sp.get_recovery_state()
    print(f"Recovery state: {recovery.name}")

    # Cleanup
    sp.clear()
    print("State cleared")
