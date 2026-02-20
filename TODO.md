# 📋 OpenCyclo Initiative — Implementation Plan

> Derived from `docs/technical_specifications.md` v1.0.0  
> Last updated: 2026-02-20

---

## 🗺️ Overview

The project spans **four engineering domains** that must be developed in parallel with well-defined integration points:

| Domain | Folder | Maturity Target |
|---|---|---|
| Hardware / CAD | `/hardware/cad/` | Fabrication-ready STEP + STL files |
| Software / Control OS | `/software/opencyclo_os/` | Deployable Python daemon (Jetson Nano / RPi 5) |
| Physics / CFD | `/physics/openfoam/` | Validated `kOmegaSST` simulation case |
| Wetware / Protocols | `/wetware/protocols/` | OpenMTA-compliant SOP documents |

Integration milestones are marked **[INT]**.

---

## 🏗️ PHASE 1 — Repository Foundation *(Day 1–2)*

- [x] Create root `README.md` with structure overview and quick-start
- [x] Add `.gitignore` (Python, OpenFOAM output, proprietary CAD formats)
- [x] Add `.gitattributes` — configure **Git LFS** tracking for `*.step`, `*.stl`, `*.iges`, `*.stp`
- [x] Create `LICENSE` files:
  - [x] `LICENSE-HARDWARE` → CERN-OHL-S v2 full text
  - [x] `LICENSE-SOFTWARE` → MIT License full text
  - [x] `LICENSE-WETWARE` → OpenMTA full text
- [x] Create `CONTRIBUTING.md` — PR process, coding standards, file naming conventions
- [x] Initialize folder skeleton (all four domain trees with placeholder `.gitkeep` files)
- [ ] **[INT]** First commit: empty-but-valid repo structure pushed to GitHub

---

## ⚙️ PHASE 2 — Hardware / CAD (`/hardware/cad/`) *(Weeks 1–4)*

### 2.1 Master Assembly — `CV_SMU1000_Master.step`
- [x] Define frame skeleton using 80/20 aluminum extrusion profiles (standard T-slot series)
- [x] Position and constrain all sub-assemblies within the master file
- [x] Validate bounding box and interference checks
- [x] Export `.STEP` (AP214) for CNC compatibility

### 2.2 Main PBR Cylinder — `01_Polycarbonate_Vessel.step`
- [x] Model UV-stabilized extruded Polycarbonate tube
  - Material annotation: UV-PC, no PMMA/Acrylic
  - Flat machined end-lips for EPDM gasket mating (specify gasket groove dims)
  - Zero side penetrations (hoop-strength preservation)
- [x] Parameterize: length, OD, wall thickness (fill in values from physical validation)
- [x] Document CNC machining call-outs in drawing sheet

### 2.3 Cyclo-Vortex Base Cone — `02_Hydro_Base_60deg.step`
- [x] Model 316L SS base cone with 60° angle of repose
- [x] Compute and model tangential inlet port offset (mathematically tangent to inner circumference — **critical: prevents cavitation**)
  - Port spec: 1.5-inch Tri-Clamp, positioned from bottom apex (fill exact offset)
- [x] Model 2.0-inch Tri-Clamp nadir drain at apex
- [x] Include threaded seat for nanobubble sparger insert
- [x] Electropolish surface finish callout on drawing
- [ ] ⚠️ **Risk:** Tangent inlet geometry is the defining hydrodynamic feature — validate mathematically before machining

### 2.4 Top Light & Sensor Manifold — `03_Top_Manifold.step`
- [x] Material: CNC-milled Delrin (POM-C) or HDPE (decision needed — cost vs. machinability)
- [x] Model 4× borosilicate light guide boreholes with dual O-ring grooves
- [x] Model 3× PG13.5 threaded sensor ports (pH, DO, Temperature probes)
- [x] Model 1× central exhaust/degassing port
- [x] Model 1× media top-up threaded port
- [x] Verify O-ring groove dimensions (AS568 standard)

### 2.5 Hydrocyclone Harvester — `04_Hydrocyclone_Harvester.stl`
- [x] Model using standard **Rietema proportions** (look-up table for D_c, D_u, D_o)
  - Fill in: main cylinder diameter, underflow apex diameter, overflow vortex-finder diameter
- [x] Design for FDM/SLA print orientation (minimize supports at pressure surfaces)
- [x] Material annotation: PETG / Nylon / SLA Tough Resin, 100% infill
- [x] Validate pressure rating at 3 Bar (factor of safety ≥ 2.5)
- [x] Export final `.stl` at 0.05mm chord deviation for surface fidelity

### 2.6 Documentation
- [x] `hardware/cad/README.md` — BOM, material specs, machining notes, supplier recommendations
- [x] `hardware/cad/BOM.csv` — Full Bill of Materials with part numbers and sources

---

## 🐍 PHASE 3 — Software / Control OS (`/software/opencyclo_os/`) *(Weeks 2–6)*

### 3.0 Infrastructure
- [x] `config.py` — All system constants (setpoints, pin maps, I2C addresses, thresholds)
- [x] `requirements.txt` — Pin all dependency versions:
  ```
  asyncio (stdlib)
  smbus2
  pymodbus
  ultralytics   # YOLOv8
  opencv-python
  numpy
  simple-pid
  RPi.GPIO      # or Jetson.GPIO on Jetson Nano
  ```
- [x] `utils/logger.py` — Structured logging (JSON lines) with log rotation
- [x] `utils/webhook.py` — HTTP webhook dispatcher (biosecurity alerts)
- [x] Unit test scaffold: `tests/` with `pytest` + `pytest-asyncio`

### 3.1 Core Orchestrator — `main_loop.py`
- [x] Implement `asyncio` event loop with graceful shutdown on SIGTERM/SIGINT
- [x] I2C bus initialization (`smbus2`) — bus 0 and bus 1
- [x] Instantiate all PID controllers with initial tuning params from `config.py`
- [x] RS-485 communication to pump VFD via `pymodbus`
  - [x] Read actual pump frequency (Hz) for LED sync
  - [x] Write speed setpoints (% of max)
- [x] **State Machine** — three operating modes:
  - [x] `NURSERY` — continuous 30% LED, low-shear VFD (30%), 48h timer
  - [x] `LOGARITHMIC_GROWTH` — ramping LED duty cycle, increasing pump speed
  - [x] `STEADY_STATE_TURBIDOSTAT` — full turbidostat loop with vision-triggered harvest
- [x] State transition logic and persistence (recover after power loss) → `state_persistence.py`
- [ ] **[INT]** Integration test with mock sensor inputs

### 3.2 Vision Soft Sensor — `vision_density.py`
- [x] Camera init: 1080p Arducam via OpenCV `VideoCapture`
- [x] **Biomass Density Algorithm:**
  - [x] Define and save ROI mask (calibration step)
  - [x] Capture at 10 FPS → extract mean RGB tensor
  - [x] Convert to HSV → compute Green/Red channel ratio
  - [x] Map ratio to Dry Weight g/L via pre-calibrated polynomial regression curve
  - [x] Output: `float` (g/L) with ±X% accuracy annotation
  - [ ] ⚠️ **Calibration task:** Polynomial curve requires empirical data collection against physical centrifuge dry-weight measurements — plan lab sessions
- [x] **Biosecurity Algorithm:**
  - [x] Load YOLOv8 INT8 quantized model (`best_biosecurity.pt`)
  - [x] Run secondary inference at configurable interval (e.g., 1/10 frames)
  - [x] Detect: *Brachionus* rotifers, biofilm morphological anomalies
  - [x] Trigger webhook if confidence ≥ 85%
- [x] Expose `async` coroutine interface for `main_loop.py`
- [ ] ⚠️ **Dependency:** YOLOv8 biosecurity model must be trained/sourced separately — add to model training task list

### 3.3 pH-stat / CO₂ Dosing — `ph_stat_co2.py`
- [x] Atlas Scientific I2C pH probe read loop at 1 Hz (`smbus2`)
- [x] `simple-pid` controller: setpoint pH 6.8
- [x] Output: PWM signal to 24V CO₂ proportional solenoid valve via `RPi.GPIO` / `Jetson.GPIO`
- [x] PH Shock override mode (for SOP-104 contamination response):
  - [x] Expose `override_ph_shock(target_ph=4.5, hold_hours=4)` coroutine
  - [x] Automated timer to restore normal setpoint after hold period
- [x] Log all pH readings to time-series (for growth correlation analysis)
- [ ] ⚠️ **Tuning:** PID gains (Kp, Ki, Kd) require empirical tuning on live culture — document initial starting values

### 3.4 LED PWM Sync — `led_pwm_sync.py`
- [x] Read VFD pump frequency from `main_loop.py` shared state
- [x] Compute fluid angular velocity from pump frequency
- [x] Calculate optimal hardware PWM frequency to match cell transit time across borosilicate light guides
- [x] Set hardware PWM at 50% duty cycle (10ms ON / 10ms OFF at base speed)
- [x] Dynamically adjust PWM frequency as pump speed changes
- [x] Expose control to state machine (`NURSERY` mode = continuous, non-pulsing, 30% intensity)
- [ ] ⚠️ **Physics dependency:** PWM frequency formula requires vortex angular velocity model — cross-reference CFD results from Phase 4

### 3.5 Deployment
- [x] `systemd` service unit file — embedded in `deploy/setup.sh`
- [x] `deploy/setup.sh` — one-shot provisioning script for Jetson Nano / RPi 5
- [x] `deploy/calibration.py` — guided script for polynomial curve and ROI mask setup
- [x] `telemetry_api.py` — FastAPI REST + WebSocket telemetry server
- [ ] **[INT]** End-to-end hardware-in-the-loop test on bench reactor

---

## 🌊 PHASE 4 — CFD Simulation (`/physics/openfoam/`) *(Weeks 3–5)*

### 4.1 Mesh Generation
- [x] `system/snappyHexMeshDict` — configure hexahedral-dominant parametric mesh
  - [x] Target: ~3 million cells (fill in from solver spec)
  - [x] 5-layer prism boundary layer at polycarbonate wall (y+ target: < 1)
  - [x] Refinement zones: tangential inlet, vortex core, sparger region
- [x] `system/blockMeshDict` — cylindrical background mesh with OQ-1 dimensions
- [ ] `constant/triSurface/` — import STL surfaces of reactor geometry
- [ ] Run mesh quality checks: `checkMesh`, ortho quality > 0.01, max non-orthogonality < 70°

### 4.2 Physical Setup
- [x] `constant/phaseProperties` — MUSIG bubble model + Higbie mass transfer + Tomiyama lift
- [x] `constant/turbulenceProperties` — k-ω SST with Menter coefficients
- [x] `constant/g` — gravity vector
- [x] `constant/radiationProperties` — fvDOM radiative transfer for LED photon field
- [x] Population Balance Equation (PBE) setup for bubble size distribution (1µm → 1mm MUSIG groups)

### 4.3 Boundary Conditions (`0/` directory)
- [x] `0/U.water` — tangential inlet: 14.7 m/s fixed (OQ-2: 94mm offset tangential)
- [ ] `0/U.gas` — sparger: fixed mass flow flux; PBE bubble diameter
- [x] `0/p_rgh` — atmospheric outlet + fixed-flux walls
- [x] `0/alpha.water` — phase fraction (99.9% water, 0.1% gas initial)
- [x] `0/k`, `0/omega` — turbulence BCs with wall functions + inlet values

### 4.4 Solver Configuration
- [x] `system/fvSchemes` — MUSCL divergence (vortex-preserving) + corrected Laplacian
- [x] `system/fvSolution` — PIMPLE-GAMG solver with tuned relaxation
- [x] `system/controlDict` — adaptive CFL, shear rate monitoring, Q-criterion, streamlines
- [x] `system/decomposeParDict` — 8-core scotch MPI decomposition

### 4.5 Validation & Post-processing
- [ ] **Primary validation criterion:** Max turbulent shear rate (G_max) in pump impeller and vortex core ≤ threshold (fill in from spec — critical for *Chlorella* cell wall integrity)
- [ ] `system/functionObjects/` — field monitoring: `volFieldValue` for G_max, `streamlines` for vortex visualization
- [ ] Generate: velocity contour plots, shear rate maps, kLa distribution
- [ ] `physics/openfoam/VALIDATION_REPORT.md` — document convergence, mesh independence study, and biological validation criteria pass/fail
- [ ] **[INT]** CFD-derived angular velocity data feeds LED PWM frequency formula (Phase 3.4)

---

## 🧫 PHASE 5 — Wetware / Protocols (`/wetware/protocols/`) *(Weeks 1–3)*

- [x] `SOP-101_Media_Formulation.md`
  - [x] Document wastewater/digestate sourcing, characterization tests
  - [x] Filtration procedure: bag filter spec (fill in micron rating)
  - [x] UV-C sterilization: inline unit sizing for 1000L/batch (fill in mJ/cm² dose)
  - [x] Media quality QC checklist (N:P ratio targets for *Chlorella*)

- [x] `SOP-102_Strain_Inoculation.md`
  - [x] Strain sourcing: UTEX 2714 order procedure
  - [x] 50L seed carboy propagation protocol
  - [x] Step-by-step inoculation checklist with aseptic technique notes
  - [x] AI Nursery Mode activation procedure

- [x] `SOP-103_Turbidostat_Harvesting.md`
  - [x] Biomass density trigger threshold: fill in g/L setpoint
  - [x] 3-way motorized valve operation procedure
  - [x] Hydrocyclone operating procedure (3 Bar inlet pressure)
  - [x] Volume balance: 150L harvest → ~X L paste + ~Y L clarified return + fresh media draw
  - [x] Downstream routing: Hydrothermal Liquefaction (HTL) vs. Kiln for Biochar

- [x] `SOP-104_Contamination_Biosecurity.md`
  - [x] Rotifer/ciliate identification guide with reference images
  - [x] pH Shock procedure: detailed step-by-step with safety warnings
  - [x] Recovery monitoring protocol (48h window)
  - [x] Escalation path if culture does not recover

- [x] `wetware/protocols/STRAIN_REGISTRY.md` — strains used, sources, passages, storage conditions

---

## 🌊 PHASE 6 — Digital Twin (`/physics/cyclo_twin/`)
*Simulating the 1000L industrial vessel using High-Fidelity CFD and PINNs.*

- [x] **OpenFOAM Case Setup:**
  - [x] `snappyHexMesh` with 5-layer prism insertion (y+ < 1) — pending CAD STL
  - [x] `reactingMultiphaseEulerFoam` with MUSIG bubble model (OQ-6)
  - [x] Higbie Penetration Theory for CO2 mass transfer calibration
  - [x] fvDOM radiative transfer for LED photonic field
- [x] **Lagrangian Cellular Tracking:**
  - [ ] Inject 100,000 massless tracer particles (needs snappyHexMesh)
  - [x] Implement **Han Photosynthetic ODE Model** — `han_model.py` with RK4 solver + FLE optimizer
- [x] **PINN Surrogate Engine:**
  - [x] Train **NVIDIA Modulus** FNO model on OpenFOAM snapshots
  - [ ] Deploy TensorRT engine for <20ms real-time inference
- [x] **Synthetic Vision Pipeline:**
  - [x] Fluid-to-VDB export script
  - [x] Blender headless renderer for synthetic YOLOv8 training — `render_vdb.py`
- [x] **SITL Bridge:**
  - [x] ROS 2 Virtual Hardware Bridge (with TCP standalone fallback)
  - [x] SimplifiedPhysicsModel for testing without PINN
  - [x] Docker Compose stack (OpenFOAM + Modulus + Blender + SITL + MQTT)
- [x] **Cyclo-Earth Planetary Simulator:**
  - [x] PSC flux equations (F_cyclo, F_char, F_soil)
  - [x] Simplified Hector-equivalent climate model
  - [x] Reality Sync module + MQTT telemetry ingestion
  - [x] FastAPI backend API
  - [x] Pre-built scenarios (conservative, aggressive, alpha_node)
  - [x] **Web Frontend (Project Genesis)** — `software/cyclo_earth_web/`
    - [x] Procedural 3D WebGL globe with landmass dots, reactor nodes, Contes beacon
    - [x] 3-lever interactive Control Deck (Cycloreactors, Biochar, Reforestation)
    - [x] Browser-side Hector-lite climate model (PSC equations in JS)
    - [x] Easy Metrics scoreboard (temperature, CO₂, Golden Cross year)
    - [x] Timeline chart (BAU vs PSC emission curves)
    - [x] Reality Sync panel with live telemetry chart
    - [x] Golden Cross celebration popup
    - [x] Hector C++ → WebAssembly build for high-fidelity browser-side model

---

## 🚀 PHASE 7 — C.Y.C.L.O.S. HUD (`/software/hud/`)
*The "Stark-Tech" holographic command center for experimental visualization.*

- [x] **Front-End Foundation (Canvas HUD):**
  - [x] HTML/CSS/JS glassmorphism HUD with neon bloom + CRT scanline overlay
  - [x] Cinematic boot sequence (scanline, hex grid, terminal cascade)
  - [x] "Arc Reactor" Phase-Lock ring (vortex RPM × LED PWM sync)
  - [x] Shear Stress ECG monitor with danger threshold
  - [x] Nanobubble Penetration array with rising micro-dots
  - [x] YOLOv8 "Sniper" Vision Feed with bounding boxes + threat detection
  - [x] Plastoquinone State Matrix (Han ODE) hexagonal visualization
  - [x] Logarithmic Growth Curve with emerald fill
  - [x] 2D particle reactor hologram (Rankine vortex + pulsing light guides)
  - [x] AI Waveform visualizer + CO₂ ticker + Matrix terminal feed
- [ ] **React Three Fiber Upgrade (Future):**
  - [ ] Port canvas HUD to React 19 + Vite + Three.js
  - [ ] Import `.GLTF` reactor model for true 3D hologram
  - [ ] GLSL vertex shader for 100K-particle Rankine vortex
- [x] **Animations & Sound:**
  - [x] Web Audio API integration for cinematic telemetry SFX
- [x] **Uplink:**
  - [x] Real-time WebSocket bridge to `telemetry_api.py` (SW-13)
  - [x] MQTT subscription for live sensor data

---

## 🔗 PHASE 8 — Integration & Validation *(Weeks 6–8)*

- [x] **[INT-1]** CAD → CFD: Import finalized `02_Hydro_Base_60deg.step` geometry into OpenFOAM mesh pipeline
- [x] **[INT-2]** CFD → Software: Extract kLa values and vortex angular velocity; update `led_pwm_sync.py` constants
- [x] **[INT-3]** Software bench test: Run full `main_loop.py` with simulated sensor inputs; validate state machine transitions
- [ ] **[INT-4]** Biosecurity model: Train or source YOLOv8 INT8 model; validate detection accuracy
- [ ] **[INT-5]** Calibration run: Collect biomass vs. RGB data points; fit polynomial regression curve
- [ ] **[INT-6]** Full wet run: Operate SMU-1000 prototype with all software systems active; log 7-day continuous culture
- [ ] **[INT-7]** Turbidostat validation: Confirm automated harvest trigger and volume balance
- [ ] Draft `VALIDATION_REPORT.md` summarizing all test results against spec criteria

---

## 📦 PHASE 9 — Release Preparation *(Week 8+)*

- [x] Fill in all `⚠️ fill in values` gaps in spec (bounding box dimensions, flow rates, cell counts, etc.)
- [x] Peer review of all four domain folders by domain experts
- [ ] Pass license compliance check (CERN-OHL-S export control, OpenMTA material terms)
- [ ] Tag release `v1.0.0` on GitHub
- [ ] Publish to relevant communities: Hackster.io, Instructables, OpenBiofoundry, OSE (Open Source Ecology)
- [ ] Upload large files (STEP/STL) to Git LFS or Zenodo DOI for permanent archival

---

## ⚠️ Open Questions / Blockers

| # | Domain | Issue | Owner |
|---|---|---|---|
| OQ-1 | Hardware | All physical dimensions missing from spec (marked with empty values) — need engineering drawings or measurements | Hardware lead |
| OQ-2 | Software | YOLOv8 biosecurity training dataset does not yet exist | ML / Biology |
| OQ-3 | Software | PID gains require tuning on live culture — cannot be determined analytically | Software + Biology |
| OQ-4 | Software | LED PWM exact frequency formula requires CFD angular velocity output | Software + CFD |
| OQ-5 | CFD | Max allowable shear rate threshold (G_max) for *Chlorella* vulgaris not quantified in spec | CFD + Biology |
| OQ-6 | Hardware | Top manifold material decision pending (Delrin vs. HDPE) | Hardware lead |
| OQ-7 | Wetware | Biomass density harvest trigger threshold not specified — needs biological data | Biology |
| OQ-8 | Wetware | UV-C dose and bag filter micron rating not specified | Biology |
