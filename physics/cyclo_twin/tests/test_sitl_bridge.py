"""
Tests — SITL Virtual Hardware Bridge
=======================================

Validates:
  1. SimplifiedPhysicsModel dynamics
  2. pH response to CO2 valve
  3. Biomass growth under illumination
  4. Temperature thermal inertia
  5. Vortex RPM tracking
  6. Command processing (standalone mode)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sitl"))

from ros2_hardware_bridge import (
    VirtualHardwareState,
    SimplifiedPhysicsModel,
    StandaloneSimulator,
)


# ──────────────────────────────────────────────
# Physics Model Tests
# ──────────────────────────────────────────────

def test_initial_state():
    """Initial state should have sensible defaults."""
    model = SimplifiedPhysicsModel()
    s = model.state
    assert s.ph == 6.8
    assert s.density_g_l == 0.1
    assert s.temperature_c == 24.0
    assert s.co2_valve_open is False
    assert s.pump_speed_pct == 0.0


def test_ph_drops_with_co2():
    """Opening CO2 valve should decrease pH."""
    model = SimplifiedPhysicsModel()
    model.state.co2_valve_open = True
    initial_ph = model.state.ph

    for _ in range(100):
        model.step(dt=0.1)

    assert model.state.ph < initial_ph


def test_ph_rises_without_co2():
    """With LEDs on and no CO2, pH should drift upward toward 7.0."""
    model = SimplifiedPhysicsModel()
    model.state.ph = 6.5
    model.state.co2_valve_open = False
    model.state.led_duty_pct = 50.0
    model.state.density_g_l = 2.0

    for _ in range(100):
        model.step(dt=0.1)

    assert model.state.ph > 6.5


def test_biomass_grows():
    """Biomass should increase with light and pump running."""
    model = SimplifiedPhysicsModel()
    model.state.led_duty_pct = 50.0
    model.state.pump_speed_pct = 50.0
    model.state.density_g_l = 0.5
    initial = model.state.density_g_l

    for _ in range(1000):
        model.step(dt=1.0)

    assert model.state.density_g_l > initial


def test_biomass_no_growth_dark():
    """Biomass should not grow significantly without light."""
    model = SimplifiedPhysicsModel()
    model.state.led_duty_pct = 0.0
    model.state.pump_speed_pct = 50.0
    model.state.density_g_l = 1.0
    initial = model.state.density_g_l

    for _ in range(100):
        model.step(dt=1.0)

    # Should stay approximately the same (no light = no growth)
    assert abs(model.state.density_g_l - initial) < initial * 0.1


def test_harvest_reduces_biomass():
    """Opening harvest valve should reduce biomass density."""
    model = SimplifiedPhysicsModel()
    model.state.density_g_l = 5.0
    model.state.harvest_valve_open = True

    for _ in range(10):
        model.step(dt=0.1)

    assert model.state.density_g_l < 5.0


def test_temperature_approaches_ambient():
    """Temperature should drift toward ambient when pump is off."""
    model = SimplifiedPhysicsModel()
    model.state.temperature_c = 30.0
    model.state.pump_speed_pct = 0.0

    for _ in range(10000):
        model.step(dt=1.0)

    # Should approach t_env (22.0)
    assert abs(model.state.temperature_c - model.t_env) < 5.0


def test_vortex_rpm_tracks_pump():
    """Vortex RPM should approach pump_speed × 68."""
    model = SimplifiedPhysicsModel()
    model.state.pump_speed_pct = 50.0

    for _ in range(100):
        model.step(dt=0.1)

    target_rpm = 50.0 * 68.0
    assert abs(model.state.vortex_rpm - target_rpm) < target_rpm * 0.3


def test_ph_bounded():
    """pH should stay within physical bounds."""
    model = SimplifiedPhysicsModel()
    model.state.co2_valve_open = True

    for _ in range(10000):
        model.step(dt=0.1)

    assert 3.0 <= model.state.ph <= 10.0


def test_density_bounded():
    """Density should never go negative."""
    model = SimplifiedPhysicsModel()
    model.state.harvest_valve_open = True
    model.state.density_g_l = 0.01

    for _ in range(100):
        model.step(dt=0.1)

    assert model.state.density_g_l > 0


# ──────────────────────────────────────────────
# Standalone Simulator Command Tests
# ──────────────────────────────────────────────

def test_command_get():
    """GET command should return state dict."""
    sim = StandaloneSimulator()
    result = sim._process_command("GET")
    assert "ph" in result
    assert "density_g_l" in result
    assert "vortex_rpm" in result


def test_command_set_co2():
    """SET co2_valve should update state."""
    sim = StandaloneSimulator()
    result = sim._process_command("SET co2_valve true")
    assert result["ok"] is True
    assert sim.physics.state.co2_valve_open is True


def test_command_set_pump():
    """SET pump_speed should update state."""
    sim = StandaloneSimulator()
    result = sim._process_command("SET pump_speed 75.0")
    assert result["ok"] is True
    assert sim.physics.state.pump_speed_pct == 75.0


def test_command_reset():
    """RESET should reinitialize physics."""
    sim = StandaloneSimulator()
    sim.physics.state.ph = 4.0
    result = sim._process_command("RESET")
    assert result["ok"] is True
    assert sim.physics.state.ph == 6.8


def test_command_unknown():
    """Unknown command should return error."""
    sim = StandaloneSimulator()
    result = sim._process_command("EXPLODE")
    assert "error" in result


def test_command_empty():
    """Empty command should return error."""
    sim = StandaloneSimulator()
    result = sim._process_command("")
    assert "error" in result


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
