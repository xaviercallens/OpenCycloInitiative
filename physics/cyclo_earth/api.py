"""
Cyclo-Earth — FastAPI Backend
==============================

REST API serving simulation results and live telemetry
to the Next.js / Deck.gl frontend.

Endpoints:
  POST /api/v1/simulate          — Run simulation with custom parameters
  GET  /api/v1/scenarios          — List pre-built scenarios
  GET  /api/v1/nodes              — Active physical reactor nodes
  GET  /api/v1/reality-sync       — SvR (Simulation vs Reality) data
  WS   /ws/globe                  — Real-time globe data stream

Spec reference: Cyclo-Earth §4 (FastAPI Backend)
"""

import json
from pathlib import Path
from typing import Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from cyclo_earth import (
    SimulationConfig, CycloReactorFleet, BiocharParams,
    SoilFeedback, ClimateBaseline,
    run_simulation, SCENARIOS, RealitySync,
)

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Cyclo-Earth Planetary Symbiosis Simulator API",
        description="REST API for the Cyclo-Earth climate simulation platform",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request Models ──

    class SimulationRequest(BaseModel):
        start_year: int = Field(default=2025, ge=2020, le=2050)
        end_year: int = Field(default=2100, ge=2030, le=2200)
        initial_modules: int = Field(default=100, ge=1, le=1_000_000)
        growth_rate: float = Field(default=2.0, ge=1.0, le=5.0)
        max_modules: int = Field(default=50_000_000, ge=1)
        biomass_growth_rate: float = Field(default=6.0, ge=1.0, le=20.0)
        biochar_yield: float = Field(default=0.35, ge=0.1, le=0.6)
        emissions_reduction_rate: float = Field(default=0.03, ge=0.0, le=0.1)

    # ── Endpoints ──

    @app.post("/api/v1/simulate")
    async def simulate(req: SimulationRequest):
        """Run a custom simulation and return results."""
        config = SimulationConfig(
            start_year=req.start_year,
            end_year=req.end_year,
            fleet=CycloReactorFleet(
                initial_modules=req.initial_modules,
                growth_rate_per_year=req.growth_rate,
                max_modules=req.max_modules,
                biomass_growth_rate=req.biomass_growth_rate,
            ),
            biochar=BiocharParams(
                pyrolysis_yield=req.biochar_yield,
            ),
            climate=ClimateBaseline(
                emissions_reduction_rate=req.emissions_reduction_rate,
            ),
        )
        results = run_simulation(config)
        return JSONResponse(content=results)

    @app.get("/api/v1/scenarios")
    async def list_scenarios():
        """List available pre-built scenarios."""
        scenarios = {}
        for name, config in SCENARIOS.items():
            scenarios[name] = {
                "initial_modules": config.fleet.initial_modules,
                "growth_rate": config.fleet.growth_rate_per_year,
                "max_modules": config.fleet.max_modules,
            }
        return JSONResponse(content={"scenarios": scenarios})

    @app.get("/api/v1/scenarios/{name}")
    async def run_scenario(name: str):
        """Run a pre-built scenario."""
        if name not in SCENARIOS:
            return JSONResponse(status_code=404, content={"error": f"Unknown scenario: {name}"})
        results = run_simulation(SCENARIOS[name])
        return JSONResponse(content=results)

    @app.get("/api/v1/nodes")
    async def list_nodes():
        """List known physical reactor nodes (stub for MQTT integration)."""
        nodes = [
            {
                "node_id": "CONTES_ALPHA_01",
                "lat": 43.8113,
                "lon": 7.3167,
                "location": "Contes, France",
                "status": "ONLINE",
                "co2_today_kg": 42.5,
                "density_g_l": 5.2,
            },
        ]
        return JSONResponse(content={"nodes": nodes, "count": len(nodes)})

    @app.get("/api/v1/reality-sync")
    async def reality_sync():
        """
        Simulation vs Reality comparison data.
        In production, this reads from TimescaleDB.
        """
        # Stub: run single-module simulation for comparison
        results = run_simulation(SCENARIOS["alpha_node"])
        rs = RealitySync()
        # Simulate some verified data
        rs.verified_co2_kg = 42.5
        rs.simulated_co2_kg = 45.0

        return JSONResponse(content={
            "node": rs.get_snapshot(),
            "simulation": {
                "years": results["years"][:10],
                "co2_ppm": results["co2_ppm"][:10],
            },
        })

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok", "service": "cyclo-earth-api"}

else:
    app = None
    print("FastAPI not available. Install: pip install fastapi uvicorn pydantic")


if __name__ == "__main__":
    if FASTAPI_AVAILABLE:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8430, log_level="info")
