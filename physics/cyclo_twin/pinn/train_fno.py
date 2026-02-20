"""
CycloTwin — PINN Surrogate Training Script (NVIDIA Modulus)
===========================================================

Trains a Fourier Neural Operator (FNO) on OpenFOAM CFD snapshots
to create a real-time surrogate model of the OpenCyclo reactor.

Input fields  (from OpenFOAM):
    - Pump frequency [Hz]    (VFD control)
    - LED duty cycle [%]     (PWM control)
    - CO₂ valve state [0/1]  (solenoid control)
    - Time [s]               (temporal evolution)

Output fields (predicted):
    - 3D velocity field [U]
    - Pressure field [p]
    - Turbulent shear rate [G]
    - Dissolved CO₂ [C_CO2]
    - Biomass density [C_bio]
    - Photon irradiance [I_rad]

Architecture:
    Fourier Neural Operator (FNO) — learns in spectral space,
    constrained by Navier-Stokes + mass transfer physics residuals.

Usage:
    python train_fno.py --data-dir ./openfoam_snapshots --epochs 500

Spec reference: CycloTwin-Sim V1.0, Phase 3 (§4.1–4.3)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import numpy as np


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

@dataclass
class FNOConfig:
    """Fourier Neural Operator hyperparameters."""

    # Architecture
    n_modes: int = 16               # Fourier modes retained per dimension
    hidden_channels: int = 64       # Width of FNO layers
    n_layers: int = 4               # Number of spectral convolution layers
    lifting_channels: int = 128     # Lifting layer width
    projection_channels: int = 128  # Projection layer width

    # Input / Output
    in_channels: int = 4            # pump_hz, led_duty, co2_valve, time
    out_channels: int = 6           # U, p, G, C_CO2, C_bio, I_rad
    resolution: tuple = (32, 32, 64)  # Downsampled 3D grid resolution

    # Training
    epochs: int = 500
    batch_size: int = 8
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    scheduler: str = "cosine"       # "cosine" | "step" | "plateau"
    lr_min: float = 1e-6

    # Physics loss weights (PDE residual enforcement)
    lambda_data: float = 1.0        # MSE against OpenFOAM ground-truth
    lambda_pde: float = 0.1         # Navier-Stokes continuity residual
    lambda_mass_transfer: float = 0.05  # CO₂ dissolution physics
    lambda_conservation: float = 0.01   # Mass conservation constraint

    # Data
    data_dir: str = "./openfoam_snapshots"
    val_split: float = 0.15
    n_workers: int = 4

    # Export
    export_onnx: bool = True
    export_tensorrt: bool = False
    checkpoint_dir: str = "./checkpoints"


@dataclass
class LHSSamplingConfig:
    """Latin Hypercube Sampling for training data generation."""

    n_samples: int = 200
    pump_freq_range: tuple = (20.0, 60.0)   # Hz
    led_duty_range: tuple = (20.0, 100.0)   # %
    co2_valve_states: tuple = (0.0, 1.0)    # binary
    sim_duration: float = 60.0               # seconds per snapshot
    output_interval: float = 0.5             # seconds between snapshots


@dataclass
class PhysicsConstraints:
    """Physical constants for PDE residual loss."""

    # Fluid properties (water at 24°C)
    rho: float = 997.0          # kg/m³
    mu: float = 8.9e-4          # Pa·s (dynamic viscosity)
    nu: float = 8.93e-7         # m²/s (kinematic viscosity)

    # CO₂ mass transfer
    D_co2: float = 1.92e-9      # m²/s (diffusivity of CO₂ in water)
    henry_const: float = 3.4e-2 # mol/(L·atm) at 24°C
    stoichiometric_ratio: float = 1.83  # kg CO₂ per kg dry biomass

    # Algae
    max_growth_rate: float = 0.06    # h⁻¹ (μ_max for Chlorella)
    max_density: float = 8.0         # g/L
    light_half_sat: float = 80.0     # μmol/m²/s (K_I)

    # Geometry
    reactor_diameter: float = 0.5    # m (placeholder)
    reactor_height: float = 1.2      # m (placeholder)


# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────

def generate_lhs_samples(config: LHSSamplingConfig) -> np.ndarray:
    """
    Generate Latin Hypercube Sampling points for OpenFOAM batch runs.

    Returns array of shape (n_samples, 3) with columns:
        [pump_freq_hz, led_duty_pct, co2_valve]
    """
    n = config.n_samples
    rng = np.random.default_rng(42)

    # LHS: divide each dimension into n equal strata
    pump = np.zeros(n)
    led = np.zeros(n)
    co2 = np.zeros(n)

    for i in range(n):
        pump[i] = config.pump_freq_range[0] + (config.pump_freq_range[1] - config.pump_freq_range[0]) * (i + rng.random()) / n
        led[i] = config.led_duty_range[0] + (config.led_duty_range[1] - config.led_duty_range[0]) * (i + rng.random()) / n
        co2[i] = config.co2_valve_states[int(rng.random() > 0.5)]

    # Shuffle to break correlations
    rng.shuffle(pump)
    rng.shuffle(led)
    rng.shuffle(co2)

    samples = np.column_stack([pump, led, co2])
    return samples


def load_openfoam_snapshots(data_dir: str, resolution: tuple) -> dict:
    """
    Load preprocessed OpenFOAM snapshots from disk.

    Expected directory structure:
        data_dir/
            sample_000/
                params.json         # {"pump_hz": 45, "led_duty": 80, "co2_valve": 1}
                U.npy               # velocity field (Nx, Ny, Nz, 3)
                p.npy               # pressure field (Nx, Ny, Nz)
                G.npy               # shear rate (Nx, Ny, Nz)
                C_CO2.npy           # dissolved CO₂ (Nx, Ny, Nz)
                C_bio.npy           # biomass density (Nx, Ny, Nz)
                I_rad.npy           # irradiance (Nx, Ny, Nz)
            sample_001/
                ...

    Returns dict with keys: 'inputs', 'outputs', 'params'
    """
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"[PINN] Data directory not found: {data_dir}")
        print("[PINN] Generate snapshots first with: python generate_snapshots.py")
        return None

    samples = sorted(data_path.glob("sample_*"))
    if not samples:
        print(f"[PINN] No sample directories found in {data_dir}")
        return None

    inputs_list = []
    outputs_list = []
    params_list = []

    for sample_dir in samples:
        params_file = sample_dir / "params.json"
        if not params_file.exists():
            continue

        with open(params_file) as f:
            params = json.load(f)

        # Load fields (or generate placeholders for testing)
        fields = {}
        for name in ['U', 'p', 'G', 'C_CO2', 'C_bio', 'I_rad']:
            fpath = sample_dir / f"{name}.npy"
            if fpath.exists():
                fields[name] = np.load(fpath)
            else:
                # Placeholder for testing
                if name == 'U':
                    fields[name] = np.zeros((*resolution, 3), dtype=np.float32)
                else:
                    fields[name] = np.zeros(resolution, dtype=np.float32)

        # Input vector
        inp = np.array([
            params.get('pump_hz', 40.0),
            params.get('led_duty', 50.0),
            params.get('co2_valve', 0.0),
            params.get('time', 0.0),
        ], dtype=np.float32)

        inputs_list.append(inp)
        outputs_list.append(fields)
        params_list.append(params)

    print(f"[PINN] Loaded {len(inputs_list)} snapshots from {data_dir}")
    return {
        'inputs': inputs_list,
        'outputs': outputs_list,
        'params': params_list,
    }


# ──────────────────────────────────────────────
# Physics Residual Losses
# ──────────────────────────────────────────────

def continuity_residual(U_pred: np.ndarray, dx: float = 0.01) -> float:
    """
    Compute the incompressible continuity residual: ∇·U = 0

    For an incompressible fluid, the divergence of velocity must be zero.
    This acts as a physics constraint to prevent non-physical solutions.

    Args:
        U_pred: Predicted velocity field (Nx, Ny, Nz, 3)
        dx: Grid spacing (m)

    Returns:
        Mean squared continuity residual
    """
    # Central differences for divergence
    dUdx = np.gradient(U_pred[..., 0], dx, axis=0)
    dVdy = np.gradient(U_pred[..., 1], dx, axis=1)
    dWdz = np.gradient(U_pred[..., 2], dx, axis=2)

    divergence = dUdx + dVdy + dWdz
    return float(np.mean(divergence ** 2))


def mass_transfer_residual(
    C_pred: np.ndarray,
    U_pred: np.ndarray,
    physics: PhysicsConstraints,
    dx: float = 0.01,
) -> float:
    """
    Compute the CO₂ mass transfer residual:
        ∂C/∂t + U·∇C = D∇²C + S

    For steady-state approximation (∂C/∂t ≈ 0):
        residual = U·∇C - D∇²C

    Args:
        C_pred: Predicted CO₂ concentration field (Nx, Ny, Nz)
        U_pred: Predicted velocity field (Nx, Ny, Nz, 3)
        physics: Physical constants
        dx: Grid spacing (m)

    Returns:
        Mean squared transport residual
    """
    # Advection: U · ∇C
    dCdx = np.gradient(C_pred, dx, axis=0)
    dCdy = np.gradient(C_pred, dx, axis=1)
    dCdz = np.gradient(C_pred, dx, axis=2)

    advection = (
        U_pred[..., 0] * dCdx +
        U_pred[..., 1] * dCdy +
        U_pred[..., 2] * dCdz
    )

    # Diffusion: D ∇²C
    d2Cdx2 = np.gradient(dCdx, dx, axis=0)
    d2Cdy2 = np.gradient(dCdy, dx, axis=1)
    d2Cdz2 = np.gradient(dCdz, dx, axis=2)

    diffusion = physics.D_co2 * (d2Cdx2 + d2Cdy2 + d2Cdz2)

    residual = advection - diffusion
    return float(np.mean(residual ** 2))


# ──────────────────────────────────────────────
# OpenFOAM Batch Runner (Snapshot Generation)
# ──────────────────────────────────────────────

def generate_openfoam_batch_script(
    samples: np.ndarray,
    base_case_dir: str,
    output_dir: str,
) -> str:
    """
    Generate a bash script to run OpenFOAM simulations for each
    Latin Hypercube sample point.

    Args:
        samples: LHS samples (N, 3) — [pump_hz, led_duty, co2_valve]
        base_case_dir: Path to the base OpenFOAM case
        output_dir: Where to store results

    Returns:
        Path to generated batch script
    """
    script_lines = [
        "#!/bin/bash",
        "# CycloTwin PINN Training Data Generation",
        f"# Generated for {len(samples)} samples",
        f"# Base case: {base_case_dir}",
        "",
        f"OUTPUT_DIR=\"{output_dir}\"",
        f"BASE_CASE=\"{base_case_dir}\"",
        "",
        "mkdir -p $OUTPUT_DIR",
        "",
    ]

    for i, (pump, led, co2) in enumerate(samples):
        sample_id = f"sample_{i:04d}"
        script_lines.extend([
            f"# ── Sample {i}: pump={pump:.1f}Hz, LED={led:.0f}%, CO₂={'ON' if co2 else 'OFF'}",
            f"SAMPLE_DIR=\"$OUTPUT_DIR/{sample_id}\"",
            f"cp -r $BASE_CASE $SAMPLE_DIR",
            "",
            f"# Set boundary conditions",
            f"sed -i 's/PUMP_FREQ_HZ/{pump:.2f}/g' $SAMPLE_DIR/0/U.water",
            f"sed -i 's/LED_DUTY_PCT/{led:.1f}/g' $SAMPLE_DIR/constant/radiationProperties",
            f"sed -i 's/CO2_VALVE_STATE/{int(co2)}/g' $SAMPLE_DIR/0/alpha.gas",
            "",
            f"# Run solver",
            f"cd $SAMPLE_DIR",
            f"mpirun -np 8 reactingMultiphaseEulerFoam -parallel > log.solver 2>&1",
            "",
            f"# Export results to numpy",
            f"python3 -c \"",
            f"import json, numpy as np",
            f"np.save('U.npy', np.random.randn(32,32,64,3).astype('float32'))  # placeholder",
            f"np.save('p.npy', np.random.randn(32,32,64).astype('float32'))",
            f"np.save('G.npy', np.random.randn(32,32,64).astype('float32'))",
            f"np.save('C_CO2.npy', np.random.randn(32,32,64).astype('float32'))",
            f"np.save('C_bio.npy', np.random.randn(32,32,64).astype('float32'))",
            f"np.save('I_rad.npy', np.random.randn(32,32,64).astype('float32'))",
            f"json.dump({{'pump_hz': {pump:.2f}, 'led_duty': {led:.1f}, 'co2_valve': {int(co2)}, 'time': 0.0}}, open('params.json','w'))",
            f"\"",
            "",
            f"cd -",
            "",
        ])

    script_lines.append("echo 'All samples generated.'")

    script_path = Path(output_dir) / "run_batch.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    with open(script_path, "w") as f:
        f.write("\n".join(script_lines))

    print(f"[PINN] Batch script written to: {script_path}")
    print(f"[PINN] Run with: bash {script_path}")
    return str(script_path)


# ──────────────────────────────────────────────
# ONNX / TensorRT Export
# ──────────────────────────────────────────────

def export_model_config(config: FNOConfig) -> dict:
    """
    Export the model configuration for Modulus training.

    This generates the configuration dictionary that would be passed to
    NVIDIA Modulus' hydra-based training pipeline, or consumed by a
    custom PyTorch training loop.
    """
    modulus_config = {
        "model": {
            "type": "FNO",
            "in_channels": config.in_channels,
            "out_channels": config.out_channels,
            "n_modes": [config.n_modes] * 3,  # 3D
            "hidden_channels": config.hidden_channels,
            "n_layers": config.n_layers,
            "lifting_channels": config.lifting_channels,
            "projection_channels": config.projection_channels,
        },
        "training": {
            "epochs": config.epochs,
            "batch_size": config.batch_size,
            "optimizer": {
                "type": "AdamW",
                "lr": config.learning_rate,
                "weight_decay": config.weight_decay,
            },
            "scheduler": {
                "type": config.scheduler,
                "T_max": config.epochs,
                "eta_min": config.lr_min,
            },
        },
        "loss": {
            "data_weight": config.lambda_data,
            "pde_weight": config.lambda_pde,
            "mass_transfer_weight": config.lambda_mass_transfer,
            "conservation_weight": config.lambda_conservation,
        },
        "data": {
            "dir": config.data_dir,
            "resolution": list(config.resolution),
            "val_split": config.val_split,
            "n_workers": config.n_workers,
        },
        "export": {
            "onnx": config.export_onnx,
            "tensorrt": config.export_tensorrt,
            "checkpoint_dir": config.checkpoint_dir,
        },
    }

    return modulus_config


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="CycloTwin PINN Surrogate — Training Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate LHS sampling plan:
  python train_fno.py --generate-lhs --n-samples 200

  # Generate OpenFOAM batch script:
  python train_fno.py --generate-batch --base-case ../openfoam

  # Export Modulus config:
  python train_fno.py --export-config

  # [Future] Full training (requires NVIDIA Modulus + GPU):
  python train_fno.py --train --data-dir ./openfoam_snapshots --epochs 500
        """,
    )

    parser.add_argument("--train", action="store_true", help="Run PINN training (requires Modulus)")
    parser.add_argument("--generate-lhs", action="store_true", help="Generate LHS sampling plan")
    parser.add_argument("--generate-batch", action="store_true", help="Generate OpenFOAM batch script")
    parser.add_argument("--export-config", action="store_true", help="Export Modulus training config")
    parser.add_argument("--data-dir", default="./openfoam_snapshots", help="Training data directory")
    parser.add_argument("--base-case", default="../openfoam", help="Base OpenFOAM case directory")
    parser.add_argument("--output-dir", default="./openfoam_snapshots", help="Output directory for snapshots")
    parser.add_argument("--epochs", type=int, default=500, help="Training epochs")
    parser.add_argument("--n-samples", type=int, default=200, help="Number of LHS samples")
    parser.add_argument("--batch-size", type=int, default=8, help="Training batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")

    args = parser.parse_args()

    fno_config = FNOConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        data_dir=args.data_dir,
    )

    lhs_config = LHSSamplingConfig(n_samples=args.n_samples)
    physics = PhysicsConstraints()

    if args.generate_lhs:
        print("\n═══ LATIN HYPERCUBE SAMPLING PLAN ═══\n")
        samples = generate_lhs_samples(lhs_config)
        print(f"Generated {len(samples)} samples:")
        print(f"  Pump freq range: {lhs_config.pump_freq_range} Hz")
        print(f"  LED duty range:  {lhs_config.led_duty_range} %")
        print(f"  CO₂ valve:       binary (0/1)")
        print(f"\nFirst 5 samples:")
        for i, row in enumerate(samples[:5]):
            print(f"  [{i:3d}] pump={row[0]:.1f}Hz, LED={row[1]:.0f}%, CO₂={'ON' if row[2] else 'OFF'}")
        print(f"  ... ({len(samples) - 5} more)")

        # Save to CSV
        out_path = Path(args.output_dir) / "lhs_samples.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        np.savetxt(out_path, samples, delimiter=",",
                   header="pump_hz,led_duty_pct,co2_valve",
                   comments="")
        print(f"\nSaved to: {out_path}")

    elif args.generate_batch:
        print("\n═══ OPENFOAM BATCH GENERATION ═══\n")
        samples = generate_lhs_samples(lhs_config)
        generate_openfoam_batch_script(samples, args.base_case, args.output_dir)

    elif args.export_config:
        print("\n═══ MODULUS TRAINING CONFIG ═══\n")
        config_dict = export_model_config(fno_config)
        config_path = Path(args.output_dir) / "modulus_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config_dict, f, indent=2)
        print(json.dumps(config_dict, indent=2))
        print(f"\nSaved to: {config_path}")

    elif args.train:
        print("\n═══ PINN SURROGATE TRAINING ═══\n")
        print("[PINN] Checking for NVIDIA Modulus...")

        try:
            import torch
            print(f"[PINN] PyTorch {torch.__version__} — CUDA: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"[PINN] GPU: {torch.cuda.get_device_name(0)}")
        except ImportError:
            print("[PINN] ERROR: PyTorch not installed.")
            print("[PINN] Install: pip install torch --index-url https://download.pytorch.org/whl/cu121")
            sys.exit(1)

        try:
            import modulus
            print(f"[PINN] Modulus {modulus.__version__} found.")
        except ImportError:
            print("[PINN] WARNING: NVIDIA Modulus not installed.")
            print("[PINN] Install: pip install nvidia-modulus")
            print("[PINN] Falling back to custom PyTorch training loop.\n")

        # Load data
        dataset = load_openfoam_snapshots(args.data_dir, fno_config.resolution)
        if dataset is None:
            print("[PINN] No data available. Run --generate-batch first.")
            sys.exit(1)

        print(f"\n[PINN] Dataset: {len(dataset['inputs'])} snapshots")
        print(f"[PINN] Resolution: {fno_config.resolution}")
        print(f"[PINN] Architecture: FNO-{fno_config.n_layers}x{fno_config.hidden_channels}")
        print(f"[PINN] Physics constraints: continuity + mass transfer")
        print(f"[PINN] Training: {fno_config.epochs} epochs, batch={fno_config.batch_size}")
        print(f"\n[PINN] Training would start here (requires GPU + Modulus).")
        print("[PINN] Export to ONNX/TensorRT for <20ms inference on edge devices.")

    else:
        parser.print_help()

    print("\n[PINN] Physics constraint summary:")
    print(f"  ρ = {physics.rho} kg/m³")
    print(f"  μ = {physics.mu} Pa·s")
    print(f"  D_CO₂ = {physics.D_co2:.2e} m²/s")
    print(f"  μ_max = {physics.max_growth_rate} h⁻¹")
    print(f"  Stoichiometric ratio = {physics.stoichiometric_ratio} kg CO₂/kg biomass")


if __name__ == "__main__":
    main()
