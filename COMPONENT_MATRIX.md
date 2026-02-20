# 🧩 OpenCyclo Initiative — Component Matrix

> Implementation tracking matrix for `CV-PBR-V1`  
> Cross-reference with `TODO.md` for full task detail  
> Last updated: 2026-02-20

---

## How to use this matrix

- **Status** column: `⬜ Not started` | `🔵 In progress` | `✅ Done` | `⚠️ Blocked`
- **Dependencies** column: lists components that must be complete (or partially complete) before this one can proceed
- **Integration Points [INT]** are highlighted in the matrix and link domains together
- Update statuses here as work progresses; keep `TODO.md` for detailed task checklists

---

## 🔵 Domain 1 — Hardware / CAD

| ID | Component | File | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| HW-01 | Master Assembly | `CV_SMU1000_Master.step` | ✅ | HW-02, HW-03, HW-04, HW-05 | — | Top-level integration via script |
| HW-02 | PBR Cylinder | `01_Polycarbonate_Vessel.step` | ✅ | — | HW-01 | UV-PC only; generated via cadquery |
| HW-03 | Cyclo-Vortex Base Cone | `02_Hydro_Base_60deg.step` | ✅ | CFD-01 (tangent inlet geometry validation) | HW-01, CFD-01 | Tangent inlet evaluated in script |
| HW-04 | Top Manifold | `03_Top_Manifold.step` | ✅ | — | HW-01 | Delrin specified |
| HW-05 | Hydrocyclone Harvester | `04_Hydrocyclone_Harvester.stl` | ✅ | — | HW-01, SW-05 | Rietema proportions script complete |
| HW-06 | Bill of Materials | `hardware/cad/BOM.csv` | ✅ | HW-01–05 | — | Supplied with mock part numbers |
| HW-07 | CAD README | `hardware/cad/README.md` | ✅ | HW-06 | — | Machining notes, material specs present |

---

## 🐍 Domain 2 — Software / Control OS

| ID | Component | File | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| SW-00 | Configuration | `config.py` | ✅ | — | All SW | Dual-profile (garage/industrial) with dataclass configs |
| SW-01 | Core Orchestrator | `main_loop.py` | ✅ | SW-00 | SW-02, SW-03, SW-04, SW-05 | State machine: Nursery → Log Growth → Turbidostat |
| SW-02 | Vision Soft Sensor | `vision_density.py` | ✅ | SW-00, SW-06 (calibration) | SW-01, SW-05 | Code complete; ⚠️ calibration data needed (OQ-2, OQ-3) |
| SW-03 | pH-stat / CO₂ Dosing | `ph_stat_co2.py` | ✅ | SW-00 | SW-01 | pH 6.8 setpoint; PH Shock override for SOP-104 |
| SW-04 | LED PWM Sync | `led_pwm_sync.py` | ✅ | SW-00, CFD-03 (angular velocity) | SW-01 | Code complete; ⚠️ PWM formula needs CFD data (OQ-4) |
| SW-05 | Harvest Valve Control | *(in main_loop.py)* | ✅ | SW-01, SW-02, HW-05 | — | Automated 3-way valve harvest implemented using RPi.GPIO |
| SW-06 | Calibration Script | `deploy/calibration.py` | ✅ | SW-00 | SW-02 | Polynomial curve fit + ROI mask for vision sensor |
| SW-07 | Logger | `utils/logger.py` | ✅ | — | SW-01 | JSON-lines, log rotation |
| SW-08 | Webhook Dispatcher | `utils/webhook.py` | ✅ | — | SW-02 | HTTP alerts for biosecurity events |
| SW-09 | systemd Service | `deploy/setup.sh` | ✅ | SW-01 | — | Embedded in setup.sh; auto-start on boot |
| SW-10 | Setup Script | `deploy/setup.sh` | ✅ | SW-00 | — | One-shot provisioning on Jetson Nano / RPi 5 |
| SW-13 | Telemetry API | `telemetry_api.py` | ✅ | SW-00 | — | FastAPI REST + WebSocket for HUD & Cyclo-Earth |
| SW-14 | State Persistence | `state_persistence.py` | ✅ | SW-00 | SW-01 | Power-loss recovery with atomic writes |
| SW-11 | YOLOv8 Model | `models/best_biosecurity.pt` | ⬜ | — | SW-02 | ⚠️ Blocked: training dataset does not exist (OQ-2) |
| SW-12 | Unit Tests | `tests/` | ✅ | SW-00, SW-01 | — | `pytest` + `pytest-asyncio` |

---

## 🌊 Domain 3 — CFD Simulation

| ID | Component | File / Directory | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| CFD-01 | Mesh Config | `system/snappyHexMeshDict` | ✅ | HW-03 geometry as STL | HW-03 (pre-machining validation), CFD-02 | 5-layer prism BL at PC wall — `snappyHexMeshDict` implemented |
| CFD-02 | Background Mesh | `system/blockMeshDict` | ✅ | — | CFD-01 | Cylindrical mesh with OQ-1 dimensions |
| CFD-03 | Phase Properties | `constant/phaseProperties` | ✅ | — | CFD-04 | MUSIG bubble model + Higbie mass transfer |
| CFD-04 | Boundary Conditions | `0/U.water`, `0/alpha.water`, `0/p_rgh`, `0/k`, `0/omega` | ✅ | CFD-03 | CFD-05 | Tangential inlet (14.7 m/s), degassing outlet |
| CFD-05 | Solver Config | `system/fvSchemes`, `system/fvSolution`, `system/controlDict` | ✅ | CFD-01–04 | CFD-06 | kOmegaSST; PIMPLE; MUSCL divergence; MPI decomp |
| CFD-06 | Simulation Run | *(cluster/local execution)* | ⬜ | CFD-01–05 | CFD-07 | `reactingMultiphaseEulerFoam`, parallel MPI |
| CFD-07 | Validation Report | `physics/openfoam/VALIDATION_REPORT.md` | ⬜ | CFD-06 | INT-1, INT-2, SW-04 | G_max ≤ threshold. Feeds LED PWM formula |
| CFD-08 | Han ODE Model | `han_model.py` | ✅ | — | CFD-07, SW-04 | Three-state photosynthetic model + FLE optimizer |
| CFD-09 | Turbulence Model | `constant/turbulenceProperties` | ✅ | — | CFD-05 | k-ω SST with Menter coefficients |
| CFD-10 | Radiation Model | `constant/radiationProperties` | ✅ | — | CFD-06 | fvDOM radiative transfer for LED photonic field |

---

## 🔬 Domain 3b — Digital Twin / SITL

| ID | Component | File / Directory | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| DT-01 | SITL Hardware Bridge | `sitl/ros2_hardware_bridge.py` | ✅ | — | DT-02 | ROS 2 + standalone TCP fallback |
| DT-02 | Simplified Physics Model | *(in DT-01)* | ✅ | — | — | Lightweight ODE model for testing without GPU |
| DT-03 | Synthetic Vision Pipeline | `synthetic_vision/render_vdb.py` | ✅ | — | SW-11 | Blender headless renderer + YOLO auto-annotation |
| DT-04 | Docker Compose Stack | `docker-compose.yml` | ✅ | — | — | 6 services: OpenFOAM, Modulus, Blender, SITL, Telemetry, MQTT |
| DT-05 | PINN Surrogate (Modulus) | `physics/cyclo_twin/pinn/train_fno.py` | ✅ | CFD-06 | — | FNO config, LHS sampling, physics residual losses, batch generation |
| DT-06 | preCICE Coupling | `physics/cyclo_twin/precice_han_adapter.py` | ✅ | CFD-06, CFD-08 | — | 100K particle vectorized Han ODE + file/preCICE/TCP modes |

---

## 🌍 Domain 5 — Cyclo-Earth Planetary Simulator

| ID | Component | File | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| CE-01 | PSC Flux Equations | `cyclo_earth.py` | ✅ | — | CE-02 | F_cyclo, F_char, F_soil |
| CE-02 | Climate Model (Hector-lite) | `cyclo_earth.py` | ✅ | CE-01 | CE-03 | Simplified carbon-cycle + ECS |
| CE-03 | Scenario System | `cyclo_earth.py` | ✅ | CE-02 | — | Conservative, Aggressive, Alpha Node presets |
| CE-04 | Reality Sync Module | `cyclo_earth.py` | ✅ | CE-01 | CE-05 | SvR (Simulation vs Reality) index |
| CE-05 | MQTT Telemetry Ingestion | `mqtt_ingest.py` | ✅ | — | CE-04 | Subscribes to `opencyclo/+/{status,co2,density}` |
| CE-06 | FastAPI Backend | `api.py` | ✅ | CE-01–05 | — | REST API for frontend + WebSocket globe stream |
| CE-07 | Web Frontend (Globe) | `software/cyclo_earth_web/` | ✅ | CE-06 | — | Procedural 3D WebGL Earth + 3-lever control deck + scoreboard + Golden Cross |
| CE-08 | Hector Wasm Build | `software/cyclo_earth_web/build_hector_wasm.sh` | ✅ | — | CE-07 | C++ → WebAssembly build script ready |
| CE-09 | Browser Climate Model | `software/cyclo_earth_web/genesis.js` | ✅ | CE-01 | CE-07 | Hector-lite in JS — PSC fluxes + ECS + timeline chart |

---

## 🧫 Domain 4 — Wetware / Biological Protocols

| ID | Component | File | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| WT-01 | Media Formulation SOP | `SOP-101_Media_Formulation.md` | ✅ | — | WT-02 | BBM (garage) + wastewater-digestate (industrial); UV-C 40 mJ/cm² |
| WT-02 | Inoculation SOP | `SOP-102_Strain_Inoculation.md` | ✅ | WT-01, HW-01 (reactor ready) | WT-03 | UTEX 2714 sourcing + flask → 50L carboy scale-up |
| WT-03 | Turbidostat Harvesting SOP | `SOP-103_Turbidostat_Harvesting.md` | ✅ | WT-02, SW-02 (vision trigger) | — | 4 g/L garage, 6 g/L industrial; hydrocyclone + siphon |
| WT-04 | Contamination / Biosecurity SOP | `SOP-104_Contamination_Biosecurity.md` | ✅ | WT-02, SW-03 (pH override) | — | pH Shock: pH 4.5 for 4h; 48h recovery protocol |
| WT-05 | Strain Registry | `STRAIN_REGISTRY.md` | ✅ | — | WT-02 | Template ready; UTEX 2714 tracking |

---

## 🔧 Domain 6 — Garage Hacker Prototype (V0.1)

| ID | Component | File | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| GP-01 | pH-Stat Control Loop | `software/garage_v01/ph_stat_loop.py` | ✅ | — | — | ADS1115 ADC + CO₂ solenoid + hysteresis band; full sim mode |
| GP-02 | Vision Growth Tracker | `software/garage_v01/vision_growth_tracker.py` | ✅ | — | — | Green saturation proxy, ASCII charts, CSV export |
| GP-03 | LED PWM Energy Saver | `software/garage_v01/led_pwm_energy_saver.py` | ✅ | — | — | 50 Hz / 50% duty FLE exploit; frequency sweep mode |
| GP-04 | Garage README | `software/garage_v01/README.md` | ✅ | GP-01–03 | — | BOM, usage instructions, expected results |

---

## 🖥️ Domain 7 — C.Y.C.L.O.S. HUD

| ID | Component | File | Status | Depends On | Blocks | Notes |
|---|---|---|---|---|---|---|
| HUD-01 | Holographic Dashboard | `software/hud/` | ✅ | — | — | 6 widgets, boot sequence, reactor hologram, CRT overlay |
| HUD-02 | Live Telemetry Bridge | `software/hud/telemetry_bridge.js` | ✅ | SW-13, DT-01 | HUD-01 | WebSocket client wired into HUD; auto-reconnect with exponential backoff |

---

## 🔗 Integration Points

| ID | Event | Producer | Consumer | Status | Notes |
|---|---|---|---|---|---|
| INT-1 | CAD geometry → CFD mesh surface | HW-03 | CFD-01 | ⬜ | Export `02_Hydro_Base_60deg` as STL for snappyHexMesh |
| INT-2 | CFD angular velocity / kLa → LED formula | CFD-07 | SW-04 | ⬜ | Blocked until CFD run completes (OQ-4) |
| INT-3 | Software bench test (simulated sensors) | SW-01–04 | Validation | ⬜ | Mock inputs; validate state machine transitions |
| INT-4 | YOLOv8 model training → deployment | SW-11 | SW-02 | ⬜ | Blocked on dataset (OQ-2) |
| INT-5 | Calibration run → polynomial curve | SW-06 | SW-02 | ⬜ | Requires live culture + physical dry-weight measurements |
| INT-6 | Full wet run (7-day continuous culture) | All SW + HW + WT | Validation | ⬜ | All domains must be complete |
| INT-7 | Turbidostat automated harvest validation | SW-02, SW-05, HW-05 | SOP-103 | ⬜ | Volume balance: confirm 15% harvest, paste + clarified water targets |

---

## ⚠️ Open Questions (Blockers)

| ID | Domain | Question | Impact | Owner |
|---|---|---|---|---|
| OQ-1 | Hardware | All physical dimensions missing from spec (empty values) | HW-02 through HW-05 cannot be finalized | Hardware lead |
| OQ-2 | Software / ML | YOLOv8 biosecurity training dataset does not exist | SW-11 → SW-02 blocked | ML + Biology |
| OQ-3 | Software | PID gains require empirical tuning on live culture | SW-03 functionally incomplete until wet run | Software + Biology |
| OQ-4 | Software / CFD | LED PWM formula requires vortex angular velocity from CFD | SW-04 blocked | Software + CFD |
| OQ-5 | CFD / Biology | G_max (critical shear threshold for *Chlorella*) not quantified in spec | CFD-07 validation criteria undefined | CFD + Biology |
| OQ-6 | Hardware | Manifold material: Delrin (POM-C) vs. HDPE — cost/machinability trade-off | HW-04 design frozen pending decision | Hardware lead |
| OQ-7 | Wetware / Software | Biomass density harvest trigger threshold not specified | SW-02 setpoint undefined; SOP-103 incomplete | Biology |
| OQ-8 | Wetware | UV-C dose and bag filter micron rating not provided | SOP-101 incomplete | Biology |

---

## 📊 Progress Summary

| Domain | Total Components | ✅ Done | 🔵 In Progress | ⚠️ Blocked | ⬜ Not Started |
|---|---|---|---|---|---|
| Hardware / CAD | 7 | 0 | 0 | 0 | 7 |
| Software / OS | 14 | 12 | 1 | 0 | 1 |
| CFD Simulation | 10 | 7 | 0 | 0 | 3 |
| Digital Twin / SITL | 6 | 6 | 0 | 0 | 0 |
| Wetware / SOPs | 5 | 5 | 0 | 0 | 0 |
| Cyclo-Earth | 9 | 8 | 0 | 0 | 1 |
| Garage Prototype | 4 | 4 | 0 | 0 | 0 |
| C.Y.C.L.O.S. HUD | 2 | 1 | 1 | 0 | 0 |
| Integration Points | 7 | 0 | 0 | 3 | 4 |
| **TOTAL** | **64** | **43** | **2** | **3** | **16** |

---

*Update this table manually or via a script as components reach completion. Cross-reference `TODO.md` for the detailed task breakdown within each component.*
