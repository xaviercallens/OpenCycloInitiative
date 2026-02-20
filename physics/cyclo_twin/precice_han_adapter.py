"""
CycloTwin — preCICE Coupling Adapter
======================================

Couples OpenFOAM Lagrangian particle tracking output to the Han
Photosynthetic ODE Model for bio-reactive digital twin simulation.

Architecture:
    ┌──────────────┐    preCICE    ┌──────────────────┐
    │  OpenFOAM    │ ◀──────────▶ │  Han ODE Solver   │
    │  Lagrangian  │              │  (this module)     │
    │  particles   │              │                    │
    └──────┬───────┘              └────────┬───────────┘
           │                               │
     Provides per-particle:         Returns per-particle:
       - position (x,y,z)            - growth rate (µ)
       - irradiance I(t)             - O₂ evolution
       - shear rate G                - CO₂ uptake
       - transit time                - photosynthetic state

The adapter reads particle trajectories from OpenFOAM (or a TCP stream),
assigns each particle a Han ODE state, evolves the ODE, and writes back
the bio-reactive source terms.

Modes:
    1. FILE   — Reads OpenFOAM particle CSV/VTK exports (post-processing)
    2. PRECICE — Live coupling via preCICE library (co-simulation)
    3. TCP    — Standalone TCP socket mode (for SITL bridge)

Usage:
    python precice_han_adapter.py --mode file --particles ./postProcessing/lagrangian
    python precice_han_adapter.py --mode precice --config precice-config.xml
    python precice_han_adapter.py --mode tcp --port 5555

Spec reference: CycloTwin-Sim V1.0, §3 (Lagrangian Biokinetics)
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

# Import Han model from sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from han_model import HanModelParams, han_ode, solve_han_model


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

@dataclass
class AdapterConfig:
    """Configuration for the preCICE adapter."""

    mode: str = "file"              # "file", "precice", "tcp"
    dt: float = 0.001               # ODE integration timestep (s)
    n_particles: int = 100_000      # Default particle count
    output_interval: float = 0.1    # Output every N seconds

    # Han model params
    han_params: HanModelParams = field(default_factory=HanModelParams)

    # preCICE
    precice_config: str = "precice-config.xml"
    precice_mesh_name: str = "LagrangianMesh"
    precice_participant: str = "HanSolver"

    # TCP fallback
    tcp_host: str = "0.0.0.0"
    tcp_port: int = 5555

    # File mode
    particle_dir: str = "./postProcessing/lagrangian"
    output_dir: str = "./han_results"

    # Geometry (for irradiance computation)
    reactor_radius: float = 0.25    # m
    light_guide_positions: list = field(default_factory=lambda: [
        {"angle": 0.0, "half_width": 0.12},
        {"angle": 1.5708, "half_width": 0.12},
        {"angle": 3.1416, "half_width": 0.12},
        {"angle": 4.7124, "half_width": 0.12},
    ])
    I_max: float = 1500.0           # µmol/m²/s at light guide surface


# ──────────────────────────────────────────────
# Particle State Manager
# ──────────────────────────────────────────────

class ParticlePopulation:
    """
    Manages the Han ODE state for a population of Lagrangian particles.

    Each particle carries:
        - position (x, y, z)
        - han_state: [x1, x2, x3] — photosynthetic state fractions
        - growth_rate: instantaneous µ (h⁻¹)
        - co2_uptake: CO₂ consumption rate (kg/m³/s)
        - o2_evolution: O₂ production rate (kg/m³/s)
    """

    def __init__(self, n_particles: int, params: HanModelParams):
        self.n = n_particles
        self.params = params

        # Han states — shape (n_particles, 3)
        self.han_states = np.zeros((n_particles, 3), dtype=np.float64)
        self.han_states[:, 0] = 1.0  # All start in resting state

        # Positions — shape (n_particles, 3)
        self.positions = np.zeros((n_particles, 3), dtype=np.float64)

        # Current irradiance per particle
        self.irradiance = np.zeros(n_particles, dtype=np.float64)

        # Output fields
        self.growth_rate = np.zeros(n_particles, dtype=np.float64)
        self.co2_uptake = np.zeros(n_particles, dtype=np.float64)
        self.o2_evolution = np.zeros(n_particles, dtype=np.float64)

        # Statistics
        self.mean_x1 = 1.0
        self.mean_x2 = 0.0
        self.mean_x3 = 0.0
        self.mean_fle = 0.0

    def update_positions(self, positions: np.ndarray):
        """Update particle positions from OpenFOAM."""
        n = min(len(positions), self.n)
        self.positions[:n] = positions[:n]

    def compute_irradiance(self, config: AdapterConfig):
        """
        Compute irradiance I(t) for each particle based on position
        relative to the light guides.

        Light guides are vertical bars on the cylinder wall. Irradiance
        falls off with distance from guide (Beer-Lambert attenuation
        through the algal suspension).
        """
        # Convert (x, y) to polar angle
        angles = np.arctan2(self.positions[:, 1], self.positions[:, 0])  # -π to π
        angles = np.mod(angles, 2 * np.pi)  # 0 to 2π

        # Distance from center
        r = np.sqrt(self.positions[:, 0]**2 + self.positions[:, 1]**2)
        r_norm = r / config.reactor_radius  # Normalized radial position

        # Irradiance: sum contributions from all light guides
        self.irradiance[:] = 0.0

        for guide in config.light_guide_positions:
            guide_angle = guide["angle"]
            half_width = guide["half_width"]  # radians

            # Angular distance from guide
            delta_angle = np.abs(np.mod(angles - guide_angle + np.pi, 2 * np.pi) - np.pi)

            # Within illuminated zone?
            in_zone = delta_angle < half_width

            # Beer-Lambert attenuation: I = I_max * exp(-µ_ext * d)
            # where d is the path length through the suspension
            # Simplified: attenuation proportional to distance from wall
            distance_from_wall = config.reactor_radius - r
            distance_from_wall = np.clip(distance_from_wall, 0, config.reactor_radius)

            extinction_coeff = 0.08  # m⁻¹ (depends on cell density)
            attenuation = np.exp(-extinction_coeff * distance_from_wall)

            # Add contribution (only if in illuminated zone)
            self.irradiance += np.where(in_zone, config.I_max * attenuation, 0.0)

    def step(self, dt: float):
        """
        Advance all particle Han ODE states by one timestep.

        Uses vectorized Euler integration (RK4 is in the scalar han_ode).
        For 100K particles, vectorized Euler is ~20x faster than per-particle RK4.
        """
        p = self.params
        x1, x2, x3 = self.han_states[:, 0], self.han_states[:, 1], self.han_states[:, 2]
        I = self.irradiance

        # Vectorized Han ODE
        dx1 = -p.sigma * I * x1 + x2 / p.tau
        dx2 = p.sigma * I * x1 - x2 / p.tau - p.kd * I * x2 + p.kr * x3
        dx3 = p.kd * I * x2 - p.kr * x3

        # Euler step
        x1_new = x1 + dt * dx1
        x2_new = x2 + dt * dx2
        x3_new = x3 + dt * dx3

        # Clamp and renormalize (conservation: x1 + x2 + x3 = 1)
        stack = np.column_stack([x1_new, x2_new, x3_new])
        stack = np.clip(stack, 0.0, 1.0)
        row_sums = stack.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0  # Prevent division by zero
        stack /= row_sums

        self.han_states = stack

        # Compute output bio-reactive source terms
        # Growth rate: µ = µ_max * x2 (active fraction drives growth)
        mu_max = 0.06 / 3600  # Convert h⁻¹ to s⁻¹
        self.growth_rate = mu_max * stack[:, 1]

        # CO₂ uptake: proportional to growth rate × stoichiometric ratio
        # 1.83 kg CO₂ per kg biomass
        self.co2_uptake = self.growth_rate * 1.83

        # O₂ evolution: photosynthetic quotient ≈ 1.0 (mol O₂ / mol CO₂)
        self.o2_evolution = self.co2_uptake * (32.0 / 44.0)

        # Update statistics
        self.mean_x1 = float(np.mean(stack[:, 0]))
        self.mean_x2 = float(np.mean(stack[:, 1]))
        self.mean_x3 = float(np.mean(stack[:, 2]))
        self.mean_fle = self.mean_x2 / (self.mean_x2 + self.mean_x3 + 1e-12)

    def get_summary(self) -> dict:
        """Return population summary statistics."""
        return {
            "n_particles": self.n,
            "mean_x1_resting": round(self.mean_x1, 4),
            "mean_x2_active": round(self.mean_x2, 4),
            "mean_x3_inhibited": round(self.mean_x3, 4),
            "fle_efficiency": round(self.mean_fle, 4),
            "mean_growth_rate_per_s": float(np.mean(self.growth_rate)),
            "mean_co2_uptake": float(np.mean(self.co2_uptake)),
            "mean_irradiance": float(np.mean(self.irradiance)),
        }


# ──────────────────────────────────────────────
# Mode: FILE (Post-Processing)
# ──────────────────────────────────────────────

def run_file_mode(config: AdapterConfig):
    """
    Process OpenFOAM Lagrangian particle exports offline.
    Reads particle positions from CSV/VTK, runs Han ODE,
    writes bio-reactive source terms back.
    """
    print("[ADAPTER] File mode — post-processing Lagrangian data")

    particle_dir = Path(config.particle_dir)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find time directories
    time_dirs = sorted([
        d for d in particle_dir.iterdir()
        if d.is_dir() and d.name.replace('.', '').isdigit()
    ], key=lambda d: float(d.name))

    if not time_dirs:
        print(f"[ADAPTER] No time directories in {particle_dir}")
        print("[ADAPTER] Expected: postProcessing/lagrangian/0.1/, 0.2/, ...")
        # Generate synthetic demo data
        print("[ADAPTER] Running with synthetic particle data...")
        run_synthetic_demo(config)
        return

    pop = ParticlePopulation(config.n_particles, config.han_params)

    for t_dir in time_dirs:
        t_val = float(t_dir.name)
        print(f"  t = {t_val:.3f}s", end="")

        # Load positions (simplified CSV format)
        pos_file = t_dir / "positions.csv"
        if pos_file.exists():
            positions = np.loadtxt(pos_file, delimiter=",", skiprows=1)
            pop.update_positions(positions[:, :3])
        else:
            # Generate random positions within cylinder for demo
            n = config.n_particles
            theta = np.random.uniform(0, 2 * np.pi, n)
            r = np.random.uniform(0, config.reactor_radius, n) ** 0.5 * config.reactor_radius
            z = np.random.uniform(-0.6, 0.6, n)
            pop.update_positions(np.column_stack([r * np.cos(theta), r * np.sin(theta), z]))

        # Compute irradiance and step ODE
        pop.compute_irradiance(config)
        pop.step(config.dt)

        summary = pop.get_summary()
        print(f"  | x2={summary['mean_x2_active']:.3f}"
              f"  FLE={summary['fle_efficiency']:.3f}"
              f"  µ={summary['mean_growth_rate_per_s']:.2e}")

        # Save output
        out_file = output_dir / f"han_state_{t_val:.3f}.json"
        with open(out_file, "w") as f:
            json.dump(summary, f, indent=2)

    print(f"\n[ADAPTER] Results written to: {output_dir}")


def run_synthetic_demo(config: AdapterConfig):
    """Run a synthetic demo with random particle positions evolving over time."""
    print("\n  ═══ SYNTHETIC DEMO: 100K particles, 1000 timesteps ═══\n")

    pop = ParticlePopulation(config.n_particles, config.han_params)

    # Generate initial positions (random within cylinder)
    n = config.n_particles
    theta = np.random.uniform(0, 2 * np.pi, n)
    r_vals = np.sqrt(np.random.uniform(0, 1, n)) * config.reactor_radius
    z = np.random.uniform(-0.6, 0.6, n)
    pop.update_positions(np.column_stack([
        r_vals * np.cos(theta),
        r_vals * np.sin(theta),
        z,
    ]))

    # Simulate vortex rotation
    angular_velocity = 2 * np.pi * 56.7  # ~3400 RPM → rad/s

    results_timeline = []
    n_steps = 1000
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()

    for step in range(n_steps):
        t = step * config.dt

        # Rotate particles (simple rigid body rotation)
        d_theta = angular_velocity * config.dt
        x = pop.positions[:, 0]
        y = pop.positions[:, 1]
        cos_dt = np.cos(d_theta)
        sin_dt = np.sin(d_theta)
        pop.positions[:, 0] = x * cos_dt - y * sin_dt
        pop.positions[:, 1] = x * sin_dt + y * cos_dt

        # Compute irradiance and step bio-kinetics
        pop.compute_irradiance(config)
        pop.step(config.dt)

        if step % 100 == 0:
            summary = pop.get_summary()
            results_timeline.append({"t": t, **summary})
            elapsed = time.time() - t0
            rate = (step + 1) / elapsed if elapsed > 0 else 0
            print(f"  step {step:5d} | t={t:.3f}s"
                  f" | x1={summary['mean_x1_resting']:.3f}"
                  f"  x2={summary['mean_x2_active']:.3f}"
                  f"  x3={summary['mean_x3_inhibited']:.3f}"
                  f"  FLE={summary['fle_efficiency']:.3f}"
                  f" | {rate:.0f} steps/s")

    elapsed = time.time() - t0
    print(f"\n  ✓ {n_steps} steps × {n} particles in {elapsed:.2f}s"
          f"  ({n_steps * n / elapsed / 1e6:.1f}M particle-steps/s)")

    # Save timeline
    timeline_file = output_dir / "synthetic_timeline.json"
    with open(timeline_file, "w") as f:
        json.dump(results_timeline, f, indent=2)
    print(f"  Timeline saved: {timeline_file}")


# ──────────────────────────────────────────────
# Mode: TCP (Standalone Bridge)
# ──────────────────────────────────────────────

def run_tcp_mode(config: AdapterConfig):
    """
    TCP socket server for real-time coupling with SITL bridge or HUD.

    Protocol:
        Client sends: JSON {"positions": [[x,y,z], ...], "dt": 0.001}
        Server replies: JSON {"states": {"mean_x2": ..., "fle": ..., ...}}
    """
    import socket

    pop = ParticlePopulation(config.n_particles, config.han_params)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((config.tcp_host, config.tcp_port))
    server.listen(1)
    print(f"[ADAPTER] TCP server listening on {config.tcp_host}:{config.tcp_port}")
    print("[ADAPTER] Waiting for SITL bridge connection...")

    while True:
        conn, addr = server.accept()
        print(f"[ADAPTER] Connected: {addr}")

        try:
            while True:
                # Read length-prefixed JSON
                header = conn.recv(4)
                if not header:
                    break
                msg_len = struct.unpack(">I", header)[0]
                data = b""
                while len(data) < msg_len:
                    chunk = conn.recv(min(4096, msg_len - len(data)))
                    if not chunk:
                        break
                    data += chunk

                request = json.loads(data.decode("utf-8"))

                # Process
                if "positions" in request:
                    positions = np.array(request["positions"], dtype=np.float64)
                    pop.update_positions(positions)

                dt = request.get("dt", config.dt)
                pop.compute_irradiance(config)
                pop.step(dt)

                # Reply
                response = json.dumps(pop.get_summary()).encode("utf-8")
                conn.sendall(struct.pack(">I", len(response)) + response)

        except (ConnectionResetError, BrokenPipeError):
            print(f"[ADAPTER] Client disconnected: {addr}")
        finally:
            conn.close()


# ──────────────────────────────────────────────
# Mode: preCICE (Co-Simulation)
# ──────────────────────────────────────────────

def run_precice_mode(config: AdapterConfig):
    """
    preCICE coupling for live co-simulation with OpenFOAM.

    Requires:
        pip install pyprecice
        preCICE library installed on system

    preCICE config must define:
        - Mesh: "LagrangianMesh" with position vertices
        - Data written by OpenFOAM: "Position", "Irradiance", "ShearRate"
        - Data read by OpenFOAM: "GrowthRate", "CO2Uptake", "O2Evolution"
    """
    try:
        import precice
    except ImportError:
        print("[ADAPTER] ERROR: pyprecice not installed.")
        print("[ADAPTER] Install: pip install pyprecice")
        print("[ADAPTER] Also need preCICE library: https://precice.org/installation-overview.html")
        print("[ADAPTER] Falling back to TCP mode instead.\n")
        run_tcp_mode(config)
        return

    print(f"[ADAPTER] preCICE mode — participant: {config.precice_participant}")
    print(f"[ADAPTER] Config: {config.precice_config}")

    # Initialize preCICE
    participant = precice.Participant(
        config.precice_participant,
        config.precice_config,
        0,  # rank
        1,  # size
    )

    mesh_name = config.precice_mesh_name
    dimensions = participant.get_mesh_dimensions(mesh_name)

    # Register mesh vertices
    pop = ParticlePopulation(config.n_particles, config.han_params)
    vertex_ids = participant.set_mesh_vertices(
        mesh_name,
        pop.positions[:, :dimensions],
    )

    # Data IDs
    read_data = {
        "Irradiance": "Irradiance",
        "ShearRate": "ShearRate",
    }
    write_data = {
        "GrowthRate": "GrowthRate",
        "CO2Uptake": "CO2Uptake",
        "O2Evolution": "O2Evolution",
    }

    participant.initialize()

    while participant.is_coupling_ongoing():
        dt = participant.get_max_time_step_size()

        # Read irradiance from OpenFOAM
        irradiance = participant.read_data(
            mesh_name, "Irradiance", vertex_ids, dt,
        )
        pop.irradiance = irradiance.flatten()

        # Step Han ODE
        pop.step(dt)

        # Write bio-reactive source terms back
        participant.write_data(
            mesh_name, "GrowthRate", vertex_ids,
            pop.growth_rate.reshape(-1, 1),
        )
        participant.write_data(
            mesh_name, "CO2Uptake", vertex_ids,
            pop.co2_uptake.reshape(-1, 1),
        )
        participant.write_data(
            mesh_name, "O2Evolution", vertex_ids,
            pop.o2_evolution.reshape(-1, 1),
        )

        participant.advance(dt)

        # Log
        summary = pop.get_summary()
        print(f"  t={dt:.4f}s | FLE={summary['fle_efficiency']:.3f}"
              f" | µ={summary['mean_growth_rate_per_s']:.2e}")

    participant.finalize()
    print("[ADAPTER] preCICE coupling complete.")


# ──────────────────────────────────────────────
# preCICE Configuration Template
# ──────────────────────────────────────────────

PRECICE_CONFIG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8" ?>
<!-- CycloTwin preCICE Configuration -->
<!-- OpenFOAM ↔ Han ODE Solver Coupling -->
<precice-configuration>

  <data:scalar name="Irradiance" />
  <data:scalar name="ShearRate" />
  <data:scalar name="GrowthRate" />
  <data:scalar name="CO2Uptake" />
  <data:scalar name="O2Evolution" />

  <mesh name="LagrangianMesh" dimensions="3">
    <use-data name="Irradiance" />
    <use-data name="ShearRate" />
    <use-data name="GrowthRate" />
    <use-data name="CO2Uptake" />
    <use-data name="O2Evolution" />
  </mesh>

  <participant name="OpenFOAM">
    <provide-mesh name="LagrangianMesh" />
    <write-data name="Irradiance" mesh="LagrangianMesh" />
    <write-data name="ShearRate" mesh="LagrangianMesh" />
    <read-data name="GrowthRate" mesh="LagrangianMesh" />
    <read-data name="CO2Uptake" mesh="LagrangianMesh" />
    <read-data name="O2Evolution" mesh="LagrangianMesh" />
  </participant>

  <participant name="HanSolver">
    <receive-mesh name="LagrangianMesh" from="OpenFOAM" />
    <read-data name="Irradiance" mesh="LagrangianMesh" />
    <read-data name="ShearRate" mesh="LagrangianMesh" />
    <write-data name="GrowthRate" mesh="LagrangianMesh" />
    <write-data name="CO2Uptake" mesh="LagrangianMesh" />
    <write-data name="O2Evolution" mesh="LagrangianMesh" />
  </participant>

  <m2n:sockets acceptor="OpenFOAM" connector="HanSolver" />

  <coupling-scheme:serial-explicit>
    <time-window-size value="0.001" />
    <max-time value="60.0" />
    <participants first="OpenFOAM" second="HanSolver" />
    <exchange data="Irradiance" mesh="LagrangianMesh" from="OpenFOAM" to="HanSolver" />
    <exchange data="ShearRate" mesh="LagrangianMesh" from="OpenFOAM" to="HanSolver" />
    <exchange data="GrowthRate" mesh="LagrangianMesh" from="HanSolver" to="OpenFOAM" />
    <exchange data="CO2Uptake" mesh="LagrangianMesh" from="HanSolver" to="OpenFOAM" />
    <exchange data="O2Evolution" mesh="LagrangianMesh" from="HanSolver" to="OpenFOAM" />
  </coupling-scheme:serial-explicit>

</precice-configuration>
"""


def generate_precice_config(output_path: str = "precice-config.xml"):
    """Generate the preCICE coupling configuration file."""
    with open(output_path, "w") as f:
        f.write(PRECICE_CONFIG_TEMPLATE)
    print(f"[ADAPTER] preCICE config written to: {output_path}")


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CycloTwin preCICE Adapter — Han ODE ↔ OpenFOAM Coupling",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  file     Post-process OpenFOAM particle data (offline)
  precice  Live preCICE co-simulation with OpenFOAM
  tcp      TCP socket server for SITL bridge

Examples:
  python precice_han_adapter.py --mode file --particles ./postProcessing/lagrangian
  python precice_han_adapter.py --mode precice --config precice-config.xml
  python precice_han_adapter.py --mode tcp --port 5555
  python precice_han_adapter.py --generate-config
        """,
    )

    parser.add_argument("--mode", choices=["file", "precice", "tcp"], default="file",
                        help="Coupling mode")
    parser.add_argument("--particles", default="./postProcessing/lagrangian",
                        help="Particle data directory (file mode)")
    parser.add_argument("--output", default="./han_results",
                        help="Output directory")
    parser.add_argument("--config", default="precice-config.xml",
                        help="preCICE config file (precice mode)")
    parser.add_argument("--port", type=int, default=5555,
                        help="TCP port (tcp mode)")
    parser.add_argument("--n-particles", type=int, default=100_000,
                        help="Number of particles")
    parser.add_argument("--dt", type=float, default=0.001,
                        help="ODE integration timestep (s)")
    parser.add_argument("--generate-config", action="store_true",
                        help="Generate preCICE config template")

    args = parser.parse_args()

    if args.generate_config:
        generate_precice_config()
        return

    config = AdapterConfig(
        mode=args.mode,
        dt=args.dt,
        n_particles=args.n_particles,
        particle_dir=args.particles,
        output_dir=args.output,
        precice_config=args.config,
        tcp_port=args.port,
    )

    print("\n  ═══════════════════════════════════════")
    print("    CycloTwin — preCICE Han Adapter")
    print("    OpenFOAM ↔ Han Photosynthetic ODE")
    print("  ═══════════════════════════════════════\n")
    print(f"  Mode:       {config.mode.upper()}")
    print(f"  Particles:  {config.n_particles:,}")
    print(f"  dt:         {config.dt}s")
    print(f"  Han σ:      {config.han_params.sigma}")
    print(f"  Han τ:      {config.han_params.tau}s")
    print(f"  I_max:      {config.I_max} µmol/m²/s")
    print()

    if config.mode == "file":
        run_file_mode(config)
    elif config.mode == "precice":
        run_precice_mode(config)
    elif config.mode == "tcp":
        run_tcp_mode(config)


if __name__ == "__main__":
    main()
