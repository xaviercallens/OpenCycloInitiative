"""
Tests — Cyclo-Earth Planetary Simulator
=========================================

Validates:
  1. PSC flux calculations (F_cyclo, F_char, F_soil)
  2. Climate model step function
  3. Full simulation output structure
  4. Golden Cross detection
  5. Reality Sync module
  6. Scenario system
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cyclo_earth import (
    compute_f_cyclo,
    compute_f_char,
    compute_f_soil,
    simple_climate_step,
    run_simulation,
    SimulationConfig,
    CycloReactorFleet,
    BiocharParams,
    SoilFeedback,
    ClimateBaseline,
    RealitySync,
    SCENARIOS,
    STOICHIOMETRIC_RATIO,
)


# ──────────────────────────────────────────────
# F_cyclo Tests
# ──────────────────────────────────────────────

def test_f_cyclo_initial():
    """Fleet of 1 module at year 0 should produce minimal CO2 capture."""
    fleet = CycloReactorFleet(initial_modules=1)
    co2_gt, n_modules = compute_f_cyclo(fleet, 2025, 2025)
    assert n_modules == 1
    assert co2_gt > 0
    assert co2_gt < 1e-6  # 1 module produces negligible Gt


def test_f_cyclo_growth():
    """Fleet should grow exponentially."""
    fleet = CycloReactorFleet(initial_modules=100, growth_rate_per_year=2.0)
    _, n_y0 = compute_f_cyclo(fleet, 2025, 2025)
    _, n_y5 = compute_f_cyclo(fleet, 2030, 2025)
    assert n_y5 > n_y0
    assert n_y5 == 100 * (2.0 ** 5)  # 3200 modules


def test_f_cyclo_saturation():
    """Fleet should saturate at max_modules."""
    fleet = CycloReactorFleet(
        initial_modules=1_000_000,
        growth_rate_per_year=10.0,
        max_modules=5_000_000,
    )
    _, n = compute_f_cyclo(fleet, 2030, 2025)
    assert n == 5_000_000


def test_f_cyclo_stoichiometry():
    """CO2 capture should respect stoichiometric ratio."""
    fleet = CycloReactorFleet(initial_modules=1)
    co2_gt, _ = compute_f_cyclo(fleet, 2025, 2025)
    # 1 module: 6 g/L/day × 1000L × 1.83 × 0.92 × 365.25 days
    expected_g = 6.0 * 1000 * 1.83 * 0.92 * 365.25
    expected_gt = expected_g / 1e15
    assert abs(co2_gt - expected_gt) / expected_gt < 0.01


# ──────────────────────────────────────────────
# F_char Tests
# ──────────────────────────────────────────────

def test_f_char_positive():
    """Biochar sequestration should be positive when biomass is supplied."""
    biochar = BiocharParams()
    f = compute_f_char(biochar, biomass_supply_gt=1.0)
    assert f > 0


def test_f_char_zero_supply():
    """No biomass → no biochar."""
    biochar = BiocharParams()
    f = compute_f_char(biochar, biomass_supply_gt=0.0)
    assert f == 0.0


def test_f_char_yield_sensitivity():
    """Higher pyrolysis yield → more carbon sequestered."""
    lo = BiocharParams(pyrolysis_yield=0.2)
    hi = BiocharParams(pyrolysis_yield=0.5)
    f_lo = compute_f_char(lo, biomass_supply_gt=1.0)
    f_hi = compute_f_char(hi, biomass_supply_gt=1.0)
    assert f_hi > f_lo


# ──────────────────────────────────────────────
# F_soil Tests
# ──────────────────────────────────────────────

def test_f_soil_zero_biochar():
    """No biochar → no soil feedback."""
    soil = SoilFeedback()
    f = compute_f_soil(soil, cumulative_biochar_gt=0.0)
    assert f == 0.0


def test_f_soil_positive():
    """Biochar should produce positive soil feedback."""
    soil = SoilFeedback()
    f = compute_f_soil(soil, cumulative_biochar_gt=0.1)
    assert f > 0


# ──────────────────────────────────────────────
# Climate Model Tests
# ──────────────────────────────────────────────

def test_climate_step_positive_emissions():
    """Positive net emissions should increase CO2."""
    climate = ClimateBaseline()
    new_co2, _ = simple_climate_step(421.0, 1.2, net_emissions_gtc=5.0, climate=climate)
    assert new_co2 > 421.0


def test_climate_step_negative_emissions():
    """Negative net emissions should decrease CO2."""
    climate = ClimateBaseline()
    new_co2, _ = simple_climate_step(421.0, 1.2, net_emissions_gtc=-5.0, climate=climate)
    assert new_co2 < 421.0


def test_climate_step_zero_emissions():
    """Zero net emissions → CO2 approximately stable."""
    climate = ClimateBaseline()
    new_co2, _ = simple_climate_step(421.0, 1.2, net_emissions_gtc=0.0, climate=climate)
    assert abs(new_co2 - 421.0) < 0.01


def test_climate_floor():
    """CO2 should never go below 200 ppm."""
    climate = ClimateBaseline()
    new_co2, _ = simple_climate_step(210.0, 0.5, net_emissions_gtc=-100.0, climate=climate)
    assert new_co2 >= 200.0


# ──────────────────────────────────────────────
# Full Simulation Tests
# ──────────────────────────────────────────────

def test_simulation_output_structure():
    """Simulation should return all required keys."""
    config = SimulationConfig(start_year=2025, end_year=2030)
    results = run_simulation(config)

    required_keys = [
        "years", "co2_ppm", "co2_ppm_bau", "temperature_c",
        "temperature_bau_c", "net_emissions_gtc", "f_cyclo_gtco2",
        "f_char_gtc", "f_soil_gtc", "n_modules",
        "cumulative_co2_removed_gt", "golden_cross_year", "config",
    ]
    for key in required_keys:
        assert key in results, f"Missing key: {key}"


def test_simulation_length():
    """Result arrays should match the number of simulated years."""
    config = SimulationConfig(start_year=2025, end_year=2030)
    results = run_simulation(config)
    assert len(results["years"]) == 6  # 2025, 2026, 2027, 2028, 2029, 2030


def test_psc_reduces_co2():
    """PSC scenario should result in lower CO2 than BAU."""
    config = SimulationConfig(
        start_year=2025,
        end_year=2060,
        fleet=CycloReactorFleet(initial_modules=1000, growth_rate_per_year=3.0),
    )
    results = run_simulation(config)
    final = len(results["years"]) - 1
    assert results["co2_ppm"][final] < results["co2_ppm_bau"][final]


def test_golden_cross_detected():
    """Aggressive scenario should find a Golden Cross."""
    results = run_simulation(SCENARIOS["psc_aggressive"])
    assert results["golden_cross_year"] is not None
    assert results["golden_cross_year"] < 2060


def test_alpha_node_single_module():
    """Alpha node scenario should have exactly 1 module throughout."""
    results = run_simulation(SCENARIOS["alpha_node"])
    for n in results["n_modules"]:
        assert n == 1


# ──────────────────────────────────────────────
# Reality Sync Tests
# ──────────────────────────────────────────────

def test_reality_sync_initial():
    """Fresh RealitySync should have zero values."""
    rs = RealitySync()
    assert rs.verified_co2_kg == 0.0
    assert rs.simulated_co2_kg == 0.0
    assert rs.get_svr_index() == 0.0


def test_reality_sync_update():
    """Updating Reality Sync should accumulate values."""
    rs = RealitySync()
    rs.update_from_telemetry(density_g_l=5.0, volume_l=1000, dt_hours=24)
    assert rs.verified_co2_kg > 0


def test_reality_sync_svr():
    """SvR index should reflect simulation vs. reality ratio."""
    rs = RealitySync()
    rs.verified_co2_kg = 45.0
    rs.simulated_co2_kg = 50.0
    svr = rs.get_svr_index()
    assert abs(svr - 0.9) < 0.01


def test_reality_sync_snapshot():
    """Snapshot should contain all required fields."""
    rs = RealitySync(node_id="TEST_NODE")
    snap = rs.get_snapshot()
    assert snap["node_id"] == "TEST_NODE"
    assert "verified_co2_kg" in snap
    assert "svr_index" in snap


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
