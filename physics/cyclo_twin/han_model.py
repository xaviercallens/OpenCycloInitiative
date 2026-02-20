"""
OpenCyclo — Han Photosynthetic ODE Model
==========================================

Implements the Han (2001) three-state photosynthetic model used
to mathematically prove the Flashing Light Effect (FLE).

The model tracks each algal cell's photosynthetic state as it
transits through the vortex light/dark zones:

  x1 (Resting)  ──photon──▶  x2 (Active)  ──damage──▶  x3 (Inhibited)
       ▲                          │                          │
       │                          │ τ recovery               │ kr repair
       └──────────────────────────┘                          │
       └─────────────────────────────────────────────────────┘

State equations (Han 2001):
  dx1/dt = -σ·I(t)·x1 + x2/τ
  dx2/dt =  σ·I(t)·x1 - x2/τ - kd·I(t)·x2 + kr·x3
  dx3/dt =  kd·I(t)·x2 - kr·x3

  x1 + x2 + x3 = 1 (conservation)

Where:
  σ  = photon absorption cross-section (m²/µmol)
  τ  = dark recovery time constant (s) ≈ plastoquinone pool turnover
  kd = photoinhibition damage rate constant (m²/µmol)
  kr = repair rate constant (1/s)
  I(t) = instantaneous photon flux (µmol/m²/s) experienced by the cell

This module:
  1. Solves the ODE for a given I(t) light history
  2. Computes the FLE efficiency metric
  3. Provides the optimization target for LED PWM frequency tuning

Spec reference: CycloTwin Digital Twin §4 (Lagrangian Biokinetics)
"""

import numpy as np
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class HanModelParams:
    """Parameters for the Han photosynthetic ODE model."""
    sigma: float = 1.5e-5       # Photon absorption cross-section (m²/µmol)
    tau: float = 0.5            # Dark recovery time constant (s)
    kd: float = 5.0e-7          # Photoinhibition damage rate (m²/µmol)
    kr: float = 5.0e-4          # Repair rate constant (1/s)
    I_max: float = 1500.0       # Max LED photon flux at surface (µmol/m²/s)


def han_ode(t: float, y: np.ndarray, I_t: float, params: HanModelParams) -> np.ndarray:
    """
    Han model ODE right-hand side.

    Args:
        t: Current time (not used directly, I_t is pre-computed)
        y: State vector [x1, x2, x3]
        I_t: Instantaneous photon flux at time t (µmol/m²/s)
        params: Model parameters

    Returns:
        dy/dt: Derivatives [dx1/dt, dx2/dt, dx3/dt]
    """
    x1, x2, x3 = y
    sigma, tau, kd, kr = params.sigma, params.tau, params.kd, params.kr

    dx1 = -sigma * I_t * x1 + x2 / tau
    dx2 = sigma * I_t * x1 - x2 / tau - kd * I_t * x2 + kr * x3
    dx3 = kd * I_t * x2 - kr * x3

    return np.array([dx1, dx2, dx3])


def solve_han_model(
    light_history: Callable[[float], float],
    duration: float,
    dt: float = 0.001,
    params: Optional[HanModelParams] = None,
    initial_state: Optional[np.ndarray] = None,
) -> dict:
    """
    Solve the Han ODE for a given light history using RK4 integration.

    Args:
        light_history: Function I(t) → photon flux at time t
        duration: Total simulation time (seconds)
        dt: Integration timestep (seconds)
        params: Han model parameters
        initial_state: Initial [x1, x2, x3] (default: all resting)

    Returns:
        Dict with time series and efficiency metrics
    """
    if params is None:
        params = HanModelParams()
    if initial_state is None:
        initial_state = np.array([1.0, 0.0, 0.0])  # All cells resting

    n_steps = int(duration / dt)
    t_arr = np.linspace(0, duration, n_steps)
    y = initial_state.copy()

    # Storage
    states = np.zeros((n_steps, 3))
    light_vals = np.zeros(n_steps)

    for i in range(n_steps):
        t = t_arr[i]
        I_t = light_history(t)
        light_vals[i] = I_t
        states[i] = y

        # RK4 integration step
        k1 = han_ode(t, y, I_t, params)
        k2 = han_ode(t + dt/2, y + dt/2 * k1, light_history(t + dt/2), params)
        k3 = han_ode(t + dt/2, y + dt/2 * k2, light_history(t + dt/2), params)
        k4 = han_ode(t + dt, y + dt * k3, light_history(t + dt), params)
        y = y + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)

        # Enforce conservation: x1 + x2 + x3 = 1
        y = np.clip(y, 0.0, 1.0)
        y /= y.sum()

    # Compute efficiency metrics
    mean_x2 = np.mean(states[:, 1])  # Mean fraction in active (processing) state
    mean_x3 = np.mean(states[:, 2])  # Mean fraction in damaged state
    fle_efficiency = mean_x2 / (mean_x2 + mean_x3 + 1e-12)  # FLE metric

    # Biomass growth rate proxy: integral of x2 over time
    growth_integral = np.trapz(states[:, 1], t_arr)

    return {
        "time": t_arr,
        "x1_resting": states[:, 0],
        "x2_active": states[:, 1],
        "x3_inhibited": states[:, 2],
        "light_history": light_vals,
        "mean_x1": np.mean(states[:, 0]),
        "mean_x2": mean_x2,
        "mean_x3": mean_x3,
        "fle_efficiency": fle_efficiency,
        "growth_integral": growth_integral,
    }


# ──────────────────────────────────────────────
# Pre-built Light History Functions
# ──────────────────────────────────────────────

def continuous_light(I_max: float = 1500.0) -> Callable[[float], float]:
    """Continuous illumination (no FLE — baseline)."""
    return lambda t: I_max


def pulsed_light(
    I_max: float = 1500.0,
    frequency_hz: float = 82.5,
    duty_cycle: float = 0.5,
) -> Callable[[float], float]:
    """
    Square-wave pulsed LED (Flashing Light Effect).

    Args:
        I_max: Peak photon flux during ON phase
        frequency_hz: Pulse frequency (Hz)
        duty_cycle: Fraction of period spent in ON phase (0-1)
    """
    period = 1.0 / frequency_hz

    def I_t(t: float) -> float:
        phase = (t % period) / period
        return I_max if phase < duty_cycle else 0.0

    return I_t


def vortex_transit_light(
    I_max: float = 1500.0,
    transit_time: float = 0.012,  # 12ms per rotation at 3400 RPM
    light_fraction: float = 0.3,  # Fraction of orbit spent in illuminated zone
) -> Callable[[float], float]:
    """
    Simulates light experienced by a cell transiting through the vortex.
    The cell sees I_max when passing the light guides, then darkness.
    """
    def I_t(t: float) -> float:
        phase = (t % transit_time) / transit_time
        return I_max if phase < light_fraction else 0.0

    return I_t


# ──────────────────────────────────────────────
# FLE Optimizer
# ──────────────────────────────────────────────

def optimize_pwm_frequency(
    pump_frequency_hz: float,
    I_max: float = 1500.0,
    duty_cycle: float = 0.5,
    freq_range: tuple = (10.0, 200.0),
    n_points: int = 50,
    sim_duration: float = 5.0,
    params: Optional[HanModelParams] = None,
) -> dict:
    """
    Scan LED PWM frequencies to find the one that maximizes FLE efficiency
    for a given pump (vortex) frequency.

    This is the computational proof that the LED must be synced to the pump.

    Returns:
        Dict with optimal frequency and scan results
    """
    frequencies = np.linspace(freq_range[0], freq_range[1], n_points)
    efficiencies = []

    for freq in frequencies:
        light = pulsed_light(I_max=I_max, frequency_hz=freq, duty_cycle=duty_cycle)
        result = solve_han_model(light, duration=sim_duration, params=params)
        efficiencies.append(result["fle_efficiency"])

    efficiencies = np.array(efficiencies)
    best_idx = np.argmax(efficiencies)

    return {
        "optimal_frequency_hz": float(frequencies[best_idx]),
        "optimal_efficiency": float(efficiencies[best_idx]),
        "pump_frequency_hz": pump_frequency_hz,
        "frequencies_scanned": frequencies.tolist(),
        "efficiencies": efficiencies.tolist(),
    }


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  🧬 Han Photosynthetic ODE Model — FLE Analysis\n")

    params = HanModelParams()

    # Compare continuous vs. pulsed light
    print("  [1] Continuous light (no FLE — baseline):")
    result_cont = solve_han_model(continuous_light(), duration=10.0, params=params)
    print(f"      x1 (resting):   {result_cont['mean_x1']:.3f}")
    print(f"      x2 (active):    {result_cont['mean_x2']:.3f}")
    print(f"      x3 (inhibited): {result_cont['mean_x3']:.3f}")
    print(f"      FLE efficiency: {result_cont['fle_efficiency']:.3f}")

    print("\n  [2] Pulsed light (82.5 Hz, 50% duty — FLE mode):")
    result_fle = solve_han_model(
        pulsed_light(frequency_hz=82.5, duty_cycle=0.5),
        duration=10.0,
        params=params,
    )
    print(f"      x1 (resting):   {result_fle['mean_x1']:.3f}")
    print(f"      x2 (active):    {result_fle['mean_x2']:.3f}")
    print(f"      x3 (inhibited): {result_fle['mean_x3']:.3f}")
    print(f"      FLE efficiency: {result_fle['fle_efficiency']:.3f}")

    improvement = (result_fle["growth_integral"] / result_cont["growth_integral"] - 1) * 100
    print(f"\n  📈 FLE growth advantage: {improvement:+.1f}%")

    # Frequency scan
    print("\n  [3] Scanning PWM frequencies (10–200 Hz)...")
    scan = optimize_pwm_frequency(pump_frequency_hz=50.0)
    print(f"      Optimal LED frequency: {scan['optimal_frequency_hz']:.1f} Hz")
    print(f"      Peak efficiency: {scan['optimal_efficiency']:.3f}")
    print()
