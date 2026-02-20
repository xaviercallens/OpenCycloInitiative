"""
Cyclo-Earth — Planetary Symbiosis Simulator Core
==================================================

Implements the PSC (Planetary Symbiotic Cycle) mathematical extensions
on top of the Hector carbon-cycle model:

  1. F_cyclo  — Cycloreactor Array CO₂ Capture Flux
  2. F_char   — Biochar Sequestration Flux (double-exponential decay)
  3. F_soil   — Soil Regeneration Feedback (NPP amplification)

The simulator runs entirely in Python for prototyping. The production
version compiles Hector to WebAssembly for browser-side execution.

Usage:
  python cyclo_earth.py --scenario psc_aggressive --years 2025-2100

Spec reference: Cyclo-Earth Specification §2
"""

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────
# Physical / Biological Constants
# ──────────────────────────────────────────────

CO2_PPM_PER_GT = 0.128           # 1 GtC ≈ 0.128 ppm atmospheric CO₂
STOICHIOMETRIC_RATIO = 1.83      # 1 g algae sequesters 1.83 g CO₂
SECONDS_PER_YEAR = 365.25 * 86400
PRE_INDUSTRIAL_CO2 = 280.0      # ppm
CURRENT_CO2 = 421.0             # ppm (2025 baseline)


@dataclass
class CycloReactorFleet:
    """Parameters for the global Cycloreactor fleet."""
    initial_modules: int = 1           # Starting 1000L modules
    growth_rate_per_year: float = 2.0  # Multiplicative annual growth
    max_modules: int = 50_000_000      # Saturation limit (50M modules)
    biomass_growth_rate: float = 6.0   # g/L/day (AI-optimized)
    volume_per_module_l: float = 1000  # Liters per module
    uptime_fraction: float = 0.92     # 92% uptime with maintenance
    capture_ratio: float = 1.83       # gCO₂ / g_biomass


@dataclass
class BiocharParams:
    """Parameters for biochar soil sequestration."""
    pyrolysis_yield: float = 0.35     # 35% of biomass → biochar
    carbon_content: float = 0.80      # 80% of biochar is carbon
    recalcitrant_fraction: float = 0.95  # 95% enters stable pool
    labile_fraction: float = 0.05      # 5% decomposes in years
    mrt_recalcitrant_years: float = 1000.0  # Mean Residence Time
    mrt_labile_years: float = 10.0
    hectares_amended_per_year: float = 1e6  # Millions of hectares
    application_rate_t_per_ha: float = 10.0  # Tonnes biochar/hectare


@dataclass
class SoilFeedback:
    """Soil regeneration feedback loop parameters."""
    soc_increase_per_biochar_t: float = 0.002  # 0.2% SOC per tonne/ha
    npp_boost_per_soc_pct: float = 0.15        # 15% NPP boost per 1% SOC
    base_terrestrial_sink_gtc: float = 3.1     # Current terrestrial sink


@dataclass
class ClimateBaseline:
    """Baseline climate parameters (simplified Hector-like model)."""
    co2_ppm: float = CURRENT_CO2
    temperature_anomaly_c: float = 1.2   # °C above pre-industrial
    ocean_sink_gtc_yr: float = 2.5       # Current ocean carbon sink
    terrestrial_sink_gtc_yr: float = 3.1
    fossil_emissions_gtc_yr: float = 10.0
    emissions_reduction_rate: float = 0.03  # 3% annual reduction (BAU+policy)
    climate_sensitivity: float = 3.0     # ECS: °C per CO₂ doubling
    co2_radiative_efficiency: float = 5.35  # W/m² per ln(CO₂/CO₂_ref)


@dataclass
class SimulationConfig:
    """Master simulation configuration."""
    start_year: int = 2025
    end_year: int = 2100
    dt_years: float = 1.0
    fleet: CycloReactorFleet = field(default_factory=CycloReactorFleet)
    biochar: BiocharParams = field(default_factory=BiocharParams)
    soil: SoilFeedback = field(default_factory=SoilFeedback)
    climate: ClimateBaseline = field(default_factory=ClimateBaseline)


# ──────────────────────────────────────────────
# PSC Flux Equations
# ──────────────────────────────────────────────

def compute_f_cyclo(fleet: CycloReactorFleet, year: int, start_year: int) -> float:
    """
    Cycloreactor Array CO₂ Capture Flux (GtCO₂/year).

    F_cyclo = N_active × μ × V × η_capture × uptime × 365

    Args:
        fleet: Fleet parameters
        year: Current simulation year
        start_year: Simulation start year

    Returns:
        CO₂ captured in Gigatonnes per year
    """
    years_elapsed = year - start_year

    # Logistic growth model for fleet expansion
    n_active = fleet.initial_modules * (fleet.growth_rate_per_year ** years_elapsed)
    n_active = min(n_active, fleet.max_modules)

    # Daily biomass production per module (grams)
    daily_biomass_g = fleet.biomass_growth_rate * fleet.volume_per_module_l

    # Annual CO₂ capture per module (grams)
    annual_co2_g = (daily_biomass_g * fleet.capture_ratio *
                    fleet.uptime_fraction * 365.25)

    # Total fleet CO₂ capture (convert grams → Gt)
    total_gt_co2 = n_active * annual_co2_g / 1e15

    return total_gt_co2, n_active


def compute_f_char(biochar: BiocharParams, biomass_supply_gt: float) -> float:
    """
    Biochar Sequestration Flux (GtC/year).

    Uses a double-exponential decay model:
      C_stored = biomass × yield × C_content × (
          f_recalcitrant × exp(-t/MRT_rec) +
          f_labile × exp(-t/MRT_lab)
      )

    For the yearly flux, we compute the net sequestration rate.

    Args:
        biochar: Biochar parameters
        biomass_supply_gt: Available biomass from reactors (GtCO₂)

    Returns:
        Carbon permanently sequestered (GtC/year)
    """
    # Convert GtCO₂ → Gt biomass → Gt biochar → GtC
    gt_biomass = biomass_supply_gt / STOICHIOMETRIC_RATIO
    gt_biochar = gt_biomass * biochar.pyrolysis_yield
    gt_carbon = gt_biochar * biochar.carbon_content

    # Stable carbon (recalcitrant pool, nearly permanent)
    stable_c = gt_carbon * biochar.recalcitrant_fraction
    # Annual loss from stable pool is negligible (MRT = 1000 years)
    stable_loss = stable_c / biochar.mrt_recalcitrant_years

    return stable_c - stable_loss


def compute_f_soil(soil: SoilFeedback, cumulative_biochar_gt: float) -> float:
    """
    Soil Regeneration Feedback — additional terrestrial carbon uptake
    from improved soil health due to biochar application.

    Every 1% increase in SOC boosts local NPP by 10-20%.

    Args:
        soil: Soil feedback parameters
        cumulative_biochar_gt: Total biochar applied to date (Gt)

    Returns:
        Additional terrestrial sink enhancement (GtC/year)
    """
    # Approximate SOC increase from cumulative biochar
    soc_increase_pct = cumulative_biochar_gt * soil.soc_increase_per_biochar_t * 1e9
    soc_increase_pct = min(soc_increase_pct, 5.0)  # Cap at 5% SOC increase

    # NPP boost
    npp_multiplier = 1.0 + soc_increase_pct * soil.npp_boost_per_soc_pct

    # Additional terrestrial sink
    enhanced_sink = soil.base_terrestrial_sink_gtc * (npp_multiplier - 1.0)

    return max(0.0, enhanced_sink)


# ──────────────────────────────────────────────
# Simplified Climate Model (Hector-equivalent)
# ──────────────────────────────────────────────

def simple_climate_step(
    co2_ppm: float,
    temp_anomaly: float,
    net_emissions_gtc: float,
    climate: ClimateBaseline,
    dt: float = 1.0,
) -> tuple[float, float]:
    """
    Single timestep of the simplified climate model.

    Uses the Bern carbon-cycle approximation + ECS.

    Args:
        co2_ppm: Current atmospheric CO₂ (ppm)
        temp_anomaly: Current temperature anomaly (°C)
        net_emissions_gtc: Net carbon emissions (GtC, negative = net removal)
        climate: Climate baseline parameters
        dt: Timestep in years

    Returns:
        (new_co2_ppm, new_temp_anomaly)
    """
    # Airborne fraction: ~45% of net emissions stay in atmosphere
    airborne_fraction = 0.45
    delta_co2 = net_emissions_gtc * airborne_fraction * CO2_PPM_PER_GT * dt

    new_co2 = co2_ppm + delta_co2
    new_co2 = max(200.0, new_co2)  # Physical floor

    # Radiative forcing (log relationship)
    forcing = climate.co2_radiative_efficiency * math.log(new_co2 / PRE_INDUSTRIAL_CO2)

    # Equilibrium temperature (with inertia)
    equilibrium_temp = climate.climate_sensitivity * math.log(new_co2 / PRE_INDUSTRIAL_CO2) / math.log(2)
    # Thermal inertia: temperature lags forcing
    tau_thermal = 15.0  # Ocean thermal inertia (years)
    new_temp = temp_anomaly + (equilibrium_temp - temp_anomaly) * dt / tau_thermal

    return new_co2, new_temp


# ──────────────────────────────────────────────
# Main Simulation Loop
# ──────────────────────────────────────────────

def run_simulation(config: Optional[SimulationConfig] = None) -> dict:
    """
    Run the Cyclo-Earth planetary simulation.

    Returns:
        Dict with year-by-year results for all metrics
    """
    if config is None:
        config = SimulationConfig()

    results = {
        "years": [],
        "co2_ppm": [],
        "co2_ppm_bau": [],          # Business-As-Usual comparison
        "temperature_c": [],
        "temperature_bau_c": [],
        "net_emissions_gtc": [],
        "f_cyclo_gtco2": [],
        "f_char_gtc": [],
        "f_soil_gtc": [],
        "n_modules": [],
        "cumulative_co2_removed_gt": [],
        "fossil_emissions_gtc": [],
    }

    co2 = config.climate.co2_ppm
    co2_bau = config.climate.co2_ppm
    temp = config.climate.temperature_anomaly_c
    temp_bau = config.climate.temperature_anomaly_c
    cumulative_removed = 0.0
    cumulative_biochar = 0.0

    n_years = int((config.end_year - config.start_year) / config.dt_years)

    for i in range(n_years + 1):
        year = config.start_year + i * config.dt_years

        # Fossil emissions (declining with policy)
        fossil = config.climate.fossil_emissions_gtc_yr * (
            (1 - config.climate.emissions_reduction_rate) ** (year - config.start_year)
        )

        # Natural sinks
        natural_sink = (config.climate.ocean_sink_gtc_yr +
                        config.climate.terrestrial_sink_gtc_yr)

        # PSC fluxes
        f_cyclo_gt, n_modules = compute_f_cyclo(config.fleet, int(year), config.start_year)
        f_cyclo_gtc = f_cyclo_gt / 3.67  # Convert GtCO₂ → GtC

        f_char = compute_f_char(config.biochar, f_cyclo_gt)
        cumulative_biochar += f_char * config.dt_years

        f_soil = compute_f_soil(config.soil, cumulative_biochar)

        # Net emissions
        psc_removal = f_cyclo_gtc + f_char + f_soil
        net_emissions = fossil - natural_sink - psc_removal
        cumulative_removed += psc_removal * config.dt_years

        # BAU: no PSC
        net_bau = fossil - natural_sink

        # Climate step
        co2, temp = simple_climate_step(co2, temp, net_emissions, config.climate, config.dt_years)
        co2_bau, temp_bau = simple_climate_step(co2_bau, temp_bau, net_bau, config.climate, config.dt_years)

        # Record
        results["years"].append(round(year, 1))
        results["co2_ppm"].append(round(co2, 2))
        results["co2_ppm_bau"].append(round(co2_bau, 2))
        results["temperature_c"].append(round(temp, 3))
        results["temperature_bau_c"].append(round(temp_bau, 3))
        results["net_emissions_gtc"].append(round(net_emissions, 4))
        results["f_cyclo_gtco2"].append(round(f_cyclo_gt, 6))
        results["f_char_gtc"].append(round(f_char, 6))
        results["f_soil_gtc"].append(round(f_soil, 6))
        results["n_modules"].append(int(n_modules))
        results["cumulative_co2_removed_gt"].append(round(cumulative_removed, 4))
        results["fossil_emissions_gtc"].append(round(fossil, 4))

    # Find the "Golden Cross" — year when net emissions go negative
    golden_cross = None
    for i, ne in enumerate(results["net_emissions_gtc"]):
        if ne < 0:
            golden_cross = results["years"][i]
            break

    results["golden_cross_year"] = golden_cross
    results["config"] = {
        "start_year": config.start_year,
        "end_year": config.end_year,
        "initial_modules": config.fleet.initial_modules,
        "fleet_growth_rate": config.fleet.growth_rate_per_year,
        "biomass_growth_rate": config.fleet.biomass_growth_rate,
    }

    return results


# ──────────────────────────────────────────────
# Pre-built Scenarios
# ──────────────────────────────────────────────

SCENARIOS = {
    "conservative": SimulationConfig(
        fleet=CycloReactorFleet(
            initial_modules=10,
            growth_rate_per_year=1.5,
            max_modules=10_000_000,
        ),
    ),
    "psc_aggressive": SimulationConfig(
        fleet=CycloReactorFleet(
            initial_modules=100,
            growth_rate_per_year=2.5,
            max_modules=100_000_000,
        ),
        biochar=BiocharParams(
            hectares_amended_per_year=5e6,
        ),
    ),
    "alpha_node": SimulationConfig(
        fleet=CycloReactorFleet(
            initial_modules=1,
            growth_rate_per_year=1.0,
            max_modules=1,
        ),
    ),
}


# ──────────────────────────────────────────────
# Reality Sync — Live Telemetry Integration
# ──────────────────────────────────────────────

class RealitySync:
    """
    Ingests live MQTT telemetry from physical Cycloreactors
    and compares against simulation predictions.

    Spec §3 Tier 3: "The Accountability Graph (SvR Index)"
    """

    def __init__(self, node_id: str = "CONTES_ALPHA_01"):
        self.node_id = node_id
        self.verified_co2_kg = 0.0
        self.simulated_co2_kg = 0.0
        self.svr_history: list[dict] = []

    def update_from_telemetry(self, density_g_l: float, volume_l: float, dt_hours: float):
        """
        Update verified CO₂ capture from live reactor data.

        Args:
            density_g_l: Current biomass density
            volume_l: Reactor volume
            dt_hours: Time since last reading
        """
        biomass_kg = density_g_l * volume_l / 1000.0
        # Growth rate approximation from density change
        co2_captured_kg = biomass_kg * STOICHIOMETRIC_RATIO * (dt_hours / 24.0) * 0.1
        self.verified_co2_kg += co2_captured_kg

    def update_simulated(self, co2_kg: float):
        """Update simulated prediction for comparison."""
        self.simulated_co2_kg += co2_kg

    def get_svr_index(self) -> float:
        """
        Simulation vs. Reality index.
        1.0 = perfect match. <1.0 = underperforming. >1.0 = overperforming.
        """
        if self.simulated_co2_kg == 0:
            return 0.0
        return self.verified_co2_kg / self.simulated_co2_kg

    def get_snapshot(self) -> dict:
        return {
            "node_id": self.node_id,
            "verified_co2_kg": round(self.verified_co2_kg, 3),
            "simulated_co2_kg": round(self.simulated_co2_kg, 3),
            "svr_index": round(self.get_svr_index(), 4),
        }


# ──────────────────────────────────────────────
# CLI Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cyclo-Earth Planetary Symbiosis Simulator")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default="psc_aggressive")
    parser.add_argument("--start", type=int, default=2025)
    parser.add_argument("--end", type=int, default=2100)
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    args = parser.parse_args()

    config = SCENARIOS[args.scenario]
    config.start_year = args.start
    config.end_year = args.end

    print(f"\n  🌍 Cyclo-Earth Planetary Symbiosis Simulator")
    print(f"  Scenario: {args.scenario}")
    print(f"  Timeline: {args.start} → {args.end}")
    print(f"  Initial Fleet: {config.fleet.initial_modules} modules")
    print(f"  Growth Rate: {config.fleet.growth_rate_per_year}x/year\n")

    results = run_simulation(config)

    # Print key milestones
    print(f"  {'Year':>6} │ {'CO₂ ppm':>10} │ {'BAU ppm':>10} │ {'ΔT °C':>8} │ "
          f"{'Net GtC':>10} │ {'Modules':>12} │ {'Removed GtCO₂':>14}")
    print(f"  {'─'*6}─┼─{'─'*10}─┼─{'─'*10}─┼─{'─'*8}─┼─"
          f"{'─'*10}─┼─{'─'*12}─┼─{'─'*14}")

    for i in range(0, len(results["years"]), 5):
        print(f"  {results['years'][i]:>6.0f} │ "
              f"{results['co2_ppm'][i]:>10.1f} │ "
              f"{results['co2_ppm_bau'][i]:>10.1f} │ "
              f"{results['temperature_c'][i]:>8.2f} │ "
              f"{results['net_emissions_gtc'][i]:>10.3f} │ "
              f"{results['n_modules'][i]:>12,} │ "
              f"{results['cumulative_co2_removed_gt'][i]:>14.3f}")

    if results["golden_cross_year"]:
        print(f"\n  🏆 GOLDEN CROSS: Net-Negative Emissions achieved in "
              f"{results['golden_cross_year']:.0f}")
    else:
        print(f"\n  ⚠️  Golden Cross not reached by {args.end}")

    # Final comparison
    final = len(results["years"]) - 1
    print(f"\n  📊 {args.end} Summary:")
    print(f"     CO₂ with PSC:  {results['co2_ppm'][final]:.1f} ppm")
    print(f"     CO₂ BAU:       {results['co2_ppm_bau'][final]:.1f} ppm")
    print(f"     Difference:    {results['co2_ppm_bau'][final] - results['co2_ppm'][final]:.1f} ppm avoided")
    print(f"     Total Removed: {results['cumulative_co2_removed_gt'][final]:.1f} GtCO₂")
    print()

    # Save results
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(__file__).parent / "simulation_results.json"

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  💾 Results saved to {out_path}\n")
