"""
Tests — Han Photosynthetic ODE Model
======================================

Validates:
  1. ODE function correctness
  2. State conservation (x1 + x2 + x3 = 1)
  3. Continuous vs. pulsed light comparison
  4. Frequency optimizer output
  5. Light history functions
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from han_model import (
    HanModelParams,
    han_ode,
    solve_han_model,
    continuous_light,
    pulsed_light,
    vortex_transit_light,
    optimize_pwm_frequency,
)


# ──────────────────────────────────────────────
# ODE Function Tests
# ──────────────────────────────────────────────

def test_ode_conservation():
    """Derivatives should sum to zero (conservation: x1+x2+x3=1)."""
    params = HanModelParams()
    y = np.array([0.5, 0.3, 0.2])
    dy = han_ode(0, y, I_t=1000.0, params=params)
    assert abs(dy.sum()) < 1e-10, f"Sum of derivatives = {dy.sum()}"


def test_ode_dark():
    """In darkness (I=0), x2 should flow back to x1, x3 should repair."""
    params = HanModelParams()
    y = np.array([0.0, 0.8, 0.2])
    dy = han_ode(0, y, I_t=0.0, params=params)
    # dx1 should be positive (recovery from x2)
    assert dy[0] > 0
    # dx2 should be negative (flowing to x1)
    assert dy[1] < 0


def test_ode_bright():
    """Under bright light with negligible x2, x1 should decrease (photon absorption dominates recovery)."""
    params = HanModelParams()
    # With x2 very small, the recovery term (x2/tau) is negligible
    # so photon absorption (sigma * I * x1) dominates
    y = np.array([0.99, 0.005, 0.005])
    dy = han_ode(0, y, I_t=2000.0, params=params)
    # dx1: -sigma*I*x1 + x2/tau = -0.0297 + 0.01 = -0.0197
    assert dy[0] < 0, f"dx1 should be negative under bright light with low x2, got {dy[0]}"


# ──────────────────────────────────────────────
# Solver Tests
# ──────────────────────────────────────────────

def test_solver_conservation():
    """State vector should remain normalized throughout simulation."""
    result = solve_han_model(continuous_light(1000.0), duration=2.0, dt=0.001)
    # Check conservation at all time steps
    total = result["x1_resting"] + result["x2_active"] + result["x3_inhibited"]
    assert np.allclose(total, 1.0, atol=1e-6), f"Max deviation from 1.0: {np.max(np.abs(total - 1.0))}"


def test_solver_returns_all_keys():
    """Solver should return dict with all expected keys."""
    result = solve_han_model(continuous_light(), duration=1.0)
    required = ["time", "x1_resting", "x2_active", "x3_inhibited",
                 "light_history", "mean_x1", "mean_x2", "mean_x3",
                 "fle_efficiency", "growth_integral"]
    for key in required:
        assert key in result, f"Missing key: {key}"


def test_solver_initial_resting():
    """Starting from all-resting should give x1 ≈ 1.0 initially."""
    result = solve_han_model(continuous_light(), duration=0.01)
    assert result["x1_resting"][0] == 1.0
    assert result["x2_active"][0] == 0.0
    assert result["x3_inhibited"][0] == 0.0


def test_solver_efficiency_bounded():
    """FLE efficiency should be between 0 and 1."""
    result = solve_han_model(pulsed_light(frequency_hz=50.0), duration=5.0)
    assert 0.0 <= result["fle_efficiency"] <= 1.0


# ──────────────────────────────────────────────
# Light History Tests
# ──────────────────────────────────────────────

def test_continuous_light():
    """Continuous light should always return I_max."""
    I = continuous_light(1500.0)
    assert I(0) == 1500.0
    assert I(0.5) == 1500.0
    assert I(100.0) == 1500.0


def test_pulsed_light_on_off():
    """Pulsed light should alternate between I_max and 0."""
    I = pulsed_light(I_max=1000.0, frequency_hz=100.0, duty_cycle=0.5)
    period = 1.0 / 100.0  # 10ms
    # At t=0 (start of ON phase)
    assert I(0) == 1000.0
    # At t=0.006 (60% of period, in OFF phase for 50% duty)
    assert I(0.006) == 0.0


def test_vortex_transit_period():
    """Vortex transit light should have correct periodicity."""
    transit = 0.012
    I = vortex_transit_light(I_max=1500.0, transit_time=transit, light_fraction=0.3)
    # At 1% of period (in light zone)
    assert I(0.001) == 1500.0
    # At 50% of period (in dark zone)
    assert I(transit * 0.5) == 0.0


# ──────────────────────────────────────────────
# Optimizer Tests
# ──────────────────────────────────────────────

def test_optimizer_output_structure():
    """Optimizer should return frequency and efficiency arrays."""
    result = optimize_pwm_frequency(
        pump_frequency_hz=50.0,
        freq_range=(20.0, 100.0),
        n_points=5,
        sim_duration=1.0,
    )
    assert "optimal_frequency_hz" in result
    assert "optimal_efficiency" in result
    assert len(result["frequencies_scanned"]) == 5
    assert len(result["efficiencies"]) == 5


def test_optimizer_frequency_in_range():
    """Optimal frequency should be within the scanned range."""
    result = optimize_pwm_frequency(
        pump_frequency_hz=50.0,
        freq_range=(10.0, 200.0),
        n_points=10,
        sim_duration=1.0,
    )
    assert 10.0 <= result["optimal_frequency_hz"] <= 200.0


def test_optimizer_efficiency_bounded():
    """All efficiencies should be between 0 and 1."""
    result = optimize_pwm_frequency(
        pump_frequency_hz=50.0,
        n_points=5,
        sim_duration=1.0,
    )
    for eff in result["efficiencies"]:
        assert 0.0 <= eff <= 1.0


# ──────────────────────────────────────────────
# Run all tests
# ──────────────────────────────────────────────

if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {test.__name__}: {e}")
            failed += 1

    print(f"\n  Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(1 if failed > 0 else 0)
