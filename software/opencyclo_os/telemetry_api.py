"""
OpenCyclo OS — Telemetry API Server
=====================================

FastAPI-based REST + WebSocket server that exposes real-time bioreactor
telemetry to external consumers:

  1. C.Y.C.L.O.S. HUD (WebSocket at 60Hz)
  2. Cyclo-Earth Planetary Simulator (MQTT bridge)
  3. Third-party dashboards

Endpoints:
  GET  /api/v1/status          — Current reactor state snapshot
  GET  /api/v1/history/{metric} — Time-series history (last N readings)
  WS   /ws/telemetry           — Real-time WebSocket stream (JSON)

Usage:
  uvicorn telemetry_api:app --host 0.0.0.0 --port 8420

Spec reference: Cyclo-Earth §4 (FastAPI Backend)
"""

import asyncio
import json
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import ACTIVE_PROFILE, OperatingState, get_config


# ──────────────────────────────────────────────
# In-Memory Telemetry Store
# ──────────────────────────────────────────────

class TelemetryStore:
    """
    Thread-safe in-memory ring buffer for telemetry data.
    Stores the last N readings per metric for the history API.
    """

    def __init__(self, max_history: int = 3600):
        self._max = max_history
        self._data: dict[str, deque] = {
            "ph": deque(maxlen=max_history),
            "density_g_l": deque(maxlen=max_history),
            "green_ratio": deque(maxlen=max_history),
            "led_freq_hz": deque(maxlen=max_history),
            "led_duty_pct": deque(maxlen=max_history),
            "pump_speed_pct": deque(maxlen=max_history),
            "pump_freq_hz": deque(maxlen=max_history),
            "temperature_c": deque(maxlen=max_history),
            "co2_valve_open": deque(maxlen=max_history),
        }
        self._state = OperatingState.IDLE
        self._state_since: float = time.time()
        self._latest: dict = {}

    def push(self, metric: str, value: float, timestamp: Optional[float] = None):
        ts = timestamp or time.time()
        entry = {"ts": ts, "value": value}
        if metric in self._data:
            self._data[metric].append(entry)
        self._latest[metric] = value

    def set_state(self, state: OperatingState):
        self._state = state
        self._state_since = time.time()

    def get_history(self, metric: str, limit: int = 100) -> list[dict]:
        if metric not in self._data:
            return []
        items = list(self._data[metric])
        return items[-limit:]

    def get_snapshot(self) -> dict:
        return {
            "profile": ACTIVE_PROFILE.name,
            "state": self._state.name,
            "state_since": self._state_since,
            "uptime_s": time.time() - self._state_since,
            "metrics": {k: v for k, v in self._latest.items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node": {
                "id": "CONTES_ALPHA_01",
                "lat": 43.8113,
                "lon": 7.3167,
                "location": "Contes, France",
            },
        }


telemetry = TelemetryStore()

# Connected WebSocket clients
ws_clients: set[WebSocket] = set()


# ──────────────────────────────────────────────
# Simulated Telemetry Producer
# ──────────────────────────────────────────────

async def simulate_telemetry():
    """
    Produces fake telemetry data for development/demo.
    In production, this is replaced by main_loop.py pushing real data.
    """
    import math
    t0 = time.time()
    telemetry.set_state(OperatingState.LOGARITHMIC_GROWTH)

    while True:
        t = time.time() - t0

        # Simulated pH: oscillates around 6.8
        ph = 6.8 + 0.15 * math.sin(t * 0.1) + 0.02 * math.sin(t * 0.7)
        telemetry.push("ph", round(ph, 3))

        # Simulated density: slowly growing
        density = 0.5 + 3.0 * (1 - math.exp(-t / 600))
        telemetry.push("density_g_l", round(density, 3))

        # Green ratio
        ratio = 1.0 + density * 0.4
        telemetry.push("green_ratio", round(ratio, 3))

        # LED
        telemetry.push("led_freq_hz", 82.5)
        telemetry.push("led_duty_pct", 50.0)

        # Pump
        telemetry.push("pump_speed_pct", 65.0)
        telemetry.push("pump_freq_hz", 32.5)

        # Temperature
        temp = 24.0 + 1.5 * math.sin(t * 0.05)
        telemetry.push("temperature_c", round(temp, 1))

        # CO2 valve
        telemetry.push("co2_valve_open", 1.0 if ph > 6.85 else 0.0)

        # Broadcast to WebSocket clients
        snapshot = telemetry.get_snapshot()
        dead = set()
        for ws in ws_clients:
            try:
                await ws.send_json(snapshot)
            except Exception:
                dead.add(ws)
        ws_clients -= dead

        await asyncio.sleep(0.5)  # 2Hz update rate


# ──────────────────────────────────────────────
# FastAPI Application
# ──────────────────────────────────────────────

if FASTAPI_AVAILABLE:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Start simulated telemetry producer in background
        task = asyncio.create_task(simulate_telemetry())
        yield
        task.cancel()

    app = FastAPI(
        title="OpenCyclo Telemetry API",
        description="Real-time bioreactor telemetry for the OpenCyclo Initiative",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for HUD frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/status")
    async def get_status():
        """Current reactor state snapshot."""
        return JSONResponse(content=telemetry.get_snapshot())

    @app.get("/api/v1/history/{metric}")
    async def get_history(
        metric: str,
        limit: int = Query(default=100, ge=1, le=3600),
    ):
        """Time-series history for a specific metric."""
        data = telemetry.get_history(metric, limit)
        if not data:
            return JSONResponse(
                status_code=404,
                content={"error": f"Unknown metric: {metric}"},
            )
        return JSONResponse(content={
            "metric": metric,
            "count": len(data),
            "data": data,
        })

    @app.get("/api/v1/metrics")
    async def list_metrics():
        """List all available telemetry metrics."""
        return JSONResponse(content={
            "metrics": list(telemetry._data.keys()),
        })

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(ws: WebSocket):
        """Real-time WebSocket telemetry stream."""
        await ws.accept()
        ws_clients.add(ws)
        try:
            while True:
                # Keep connection alive; client doesn't need to send anything
                await ws.receive_text()
        except WebSocketDisconnect:
            ws_clients.discard(ws)

    @app.get("/api/v1/co2")
    async def get_co2_stats():
        """
        Cumulative CO₂ sequestration estimate.
        Used by Cyclo-Earth Reality Sync module.
        """
        density_history = telemetry.get_history("density_g_l", limit=3600)
        if not density_history:
            return JSONResponse(content={
                "co2_kg_total": 0.0,
                "co2_kg_today": 0.0,
            })

        # Rough estimate: 1g algae sequesters ~1.83g CO₂ (stoichiometric)
        # Using the latest density * reactor volume * stoichiometric ratio
        cfg = get_config()
        reactor_volume_l = 19.0 if ACTIVE_PROFILE.name == "GARAGE" else 1000.0
        latest_density = density_history[-1]["value"]
        biomass_kg = latest_density * reactor_volume_l / 1000.0
        co2_kg = biomass_kg * 1.83  # CO₂ fixation ratio

        return JSONResponse(content={
            "co2_kg_total": round(co2_kg, 3),
            "co2_kg_today": round(co2_kg * 0.1, 3),  # Placeholder daily rate
            "reactor_volume_l": reactor_volume_l,
            "biomass_density_g_l": latest_density,
            "stoichiometric_ratio": 1.83,
        })

else:
    # Stub when FastAPI is not installed
    app = None
    print("WARNING: FastAPI not installed. Telemetry API disabled.")
    print("Install with: pip install fastapi uvicorn")


if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8420, log_level="info")
    else:
        print("FastAPI is required. Install: pip install fastapi uvicorn")
