# 📂 OPENCYCLO INITIATIVE: TECHNICAL ASSET SPECIFICATIONS

**Repository Name:** `OpenCycloInitiative/CV-PBR-V1`

**Document Path:** `//docs/technical_specifications.md`

**Version:** 1.0.0 (Global Open-Source Release)

**License:** CERN-OHL-S (Hardware), MIT (Software), OpenMTA (Wetware)

This document details the exact engineering specifications, software architectures, physics models, and standard operating procedures contained within the OpenCyclo V1.0 repository. It serves as the master technical index for engineers, software developers, and microbiologists deploying the system.

---

## 📐 1. CAD FILES & HARDWARE ASSEMBLIES (`/hardware/cad/`)

All hardware files are provided in fully parameterized `.STEP` format for cross-platform CNC machining compatibility, alongside `.STL` files optimized for industrial 3D printing.

### **1.1. Master Assembly (`CV_SMU1000_Master.step`)**

* **Description:** The complete 1,000-Liter Standard Modular Unit (SMU-1000) fully assembled with the 80/20 aluminum extrusion frame, structural mounts, and fluidic plumbing loops.
* **Bounding Box:** .

### **1.2. Main PBR Cylinder (`01_Polycarbonate_Vessel.step`)**

* **Material Spec:** UV-Stabilized Extruded Polycarbonate (PC). *(Warning: Acrylic/PMMA is strictly prohibited due to rapid degradation under continuous PAR/UV exposure).*
* **Dimensions:**  length,  Outer Diameter (OD),  wall thickness.
* **Machining:** Zero side penetrations to maintain hoop strength under hydrostatic pressure. Both ends feature machined flat lips for flush EPDM gasket mating.

### **1.3. Cyclo-Vortex Base Cone (`02_Hydro_Base_60deg.step`)**

* **Material Spec:** 316L Stainless Steel (Food-grade, Electropolished).
* **Geometry:**  angle of repose to prevent biological settling and eliminate dead-zones.
* **Tangential Inlet:**  (1.5-inch) Tri-Clamp port located  vertically from the bottom apex. The entry vector is offset mathematically to be perfectly tangent to the inner circumference, inducing the Rankine vortex without fluid cavitation.
* **Nadir Drain:**  (2.0-inch) Tri-Clamp bottom port housing the primary pump draw and the 3D-printed/sintered nanobubble sparger insert.

### **1.4. Top Light & Sensor Manifold (`03_Top_Manifold.step`)**

* **Material Spec:** CNC-milled Delrin (POM-C) or High-Density Polyethylene (HDPE).
* **Ports:**
* 4x  boreholes with dual O-ring grooves for the Borosilicate Light Guides.
* 3x  PG13.5 threaded ports for industrial sensor probes (pH, DO, Temp).
* 1x  central exhaust port for  degassing and emergency pressure relief.
* 1x  threaded port for continuous media top-up.



### **1.5. Hydrocyclone Harvester (`04_Hydrocyclone_Harvester.stl`)**

* **Material Spec:** 3D Printed PETG, Nylon, or SLA Tough Resin (100% Infill for pressure resistance up to 3 Bar).
* **Geometry:** Standard Rietema proportions.  main cylinder diameter,  underflow apex (algal paste),  overflow vortex finder (clarified water).
* **Function:** Uses centrifugal force from the main pump bypass to passively concentrate  culture into a  thick paste without requiring high-energy mechanical centrifuges.

---

## 🐍 2. PYTHON CONTROL SCRIPTS (`/software/opencyclo_os/`)

The software stack is an asynchronous, edge-computing architecture optimized for NVIDIA Jetson Nano or Raspberry Pi 5 (8GB) running a Debian-based OS.

### **2.1. Core Orchestrator (`main_loop.py`)**

* **Libraries:** `asyncio`, `smbus2`, `pymodbus`.
* **Function:** The central daemon. Initializes I2C buses, instantiates PID controllers, communicates with the Pump VFD via RS-485, and manages the state-machine (Nursery  Logarithmic Growth  Steady-State Turbidostat).

### **2.2. Computer Vision Soft Sensor (`vision_density.py`)**

* **Libraries:** `ultralytics` (YOLOv8 INT8 Quantized), `OpenCV`, `NumPy`.
* **Function:** Captures 10 FPS from the 1080p Arducam looking through the viewport.
* **Algorithm (Density):** Masks the region of interest, extracts the mean RGB tensor, converts to HSV space, and maps the Green/Red ratio to a pre-calibrated polynomial regression curve. Outputs Biomass Density (Dry Weight g/L) with  accuracy.
* **Algorithm (Bio-Security):** Runs a secondary YOLOv8 inference to detect microscopic grazers (e.g., *Brachionus* rotifers) or biofilm buildup via morphological anomalies, triggering webhooks if confidence exceeds 85%.

### **2.3. Carbon Dosing PID Controller (`ph_stat_co2.py`)**

* **Libraries:** `simple-pid`, `RPi.GPIO`.
* **Function:** Asynchronous loop reading the Atlas Scientific I2C pH probe at 1 Hz.
* **Logic:** Algae consume dissolved CO₂, raising the pH.
* **Setpoint:** pH 6.8.
* When pH , the PID controller sends a PWM signal to the 24V CO₂ proportional solenoid valve, injecting nanobubbles until pH drops back to the setpoint. Ensures 100% CO₂ absorption with zero atmospheric outgassing.



### **2.4. Flashing Light Effect Sync (`led_pwm_sync.py`)**

* **Function:** Manages the LED arrays to exploit the biological Plastoquinone dark-phase turnover rate.
* **Logic:** Reads the VFD pump frequency to calculate fluid angular velocity. If the vortex spins faster, the script increases the hardware PWM frequency () to match the exact millisecond cells cross the illuminated glass guides.
* **Impact:** Maintains a 50% duty cycle (e.g., 10ms ON, 10ms OFF), cutting lighting electrical OPEX by half while maintaining maximum photon use efficiency.

---

## 🌊 3. CFD SIMULATION MODELS (`/physics/openfoam/`)

Provided as ready-to-run OpenFOAM (v2312) case files to validate fluid mechanics, scale-up designs, and map the Volumetric Mass Transfer Coefficient ().

### **3.1. Solver & Mesh Specifications (`snappyHexMeshDict`)**

* **Solver:** `reactingMultiphaseEulerFoam` (Handles gas-liquid Eulerian-Eulerian multiphase flow with interphase mass transfer).
* **Mesh:** Hexahedral-dominant parametric mesh generating  cells.
* **Refinement:** 5-layer prism boundary layer at the outer Polycarbonate wall to ensure , accurately resolving the high-shear illuminated zone.

### **3.2. Boundary Conditions & Physics (`0/` directory)**

* **Turbulence Model:**  (Shear Stress Transport). Standard for highly swirling/cyclonic flows.
* **Tangential Inlet (`U.water`):** Fixed flow rate of .
* **Bottom Sparger (`U.gas`):** Fixed mass flow flux. Bubble diameter defined via Population Balance Equation (PBE), initialized at  ( nanobubbles).
* **Top Vent (`p_rgh`):** `degassingBoundary` (Allows total pressure release for gas phase to escape; acts as a slip wall reflecting the liquid phase back).

### **3.3. Validation Criteria**

The CFD output must mathematically prove that the maximum turbulent shear rate () inside the pump impeller and vortex core does not exceed . Shear above this threshold physically shreds *Chlorella* cell walls, causing immediate culture crash.

---

## 🧫 4. BIOLOGICAL SOPs (`/wetware/protocols/`)

Standard Operating Procedures governing the biological "Wetware." Formatted for OpenMTA (Open Material Transfer Agreement) compliance, designed for operators without advanced microbiology degrees.

### **SOP-101: Media Formulation (The Wastewater Nexus)**

* **Objective:** Prepare nutrient-rich growth media with zero synthetic fossil fertilizers.
* **Primary Source:** Filtered primary effluent from municipal wastewater or agricultural anaerobic digestate (naturally rich in  and ).
* **Filtration:** Pass raw effluent through a  mechanical bag filter to remove suspended solids that block light penetration.
* **Sterilization:** Pass through a high-intensity inline UV-C sterilizer ( dose) to eliminate wild, competing cyanobacteria and predatory protozoa.

### **SOP-102: Strain Inoculation & Start-Up**

* **Target Strain:** *Chlorella vulgaris* (UTEX 2714) or *Scenedesmus obliquus*. (Both possess the high shear-stress tolerance required for the cyclonic vortex).
* **Procedure:**
1. Fill the SMU-1000 with 950 L of prepared media (SOP-101).
2. Engage the vortex pump at 30% VFD capacity (low shear for fragile new cells).
3. Aseptically inject 50 L of dense seed culture (grown in a 50L lab carboy).
4. **AI Nursery Mode:** The AI OS locks LEDs to continuous (non-pulsing) 30% intensity for the first 48 hours to allow photo-acclimation.



### **SOP-103: Steady-State Turbidostat Harvesting**

* **Objective:** Maintain perpetual exponential growth.
* **Trigger:** AI Soft Sensor detects Biomass Density .
* **Action:** Automated 3-way motorized ball valve opens.
* **Process:**  of culture (15% volume) is diverted through the 3D-printed Hydrocyclone at 3 Bar pressure.
* **Output:**  of thick algal paste is collected in the harvest vat (send to HTL for Bio-fuels or Kiln for Biochar).  of clarified water returns to the reactor. AI automatically draws  of fresh wastewater media to restore total volume.

### **SOP-104: Contamination & Bio-Security (The "pH Shock")**

* **Trigger:** Vision AI detects irregular particle movement or sudden density drops despite optimal lighting and nutrients (indicative of rotifer/ciliate predators grazing on the algae).
* **Remediation:** Do *not* dump the 1,000L reactor.
1. Temporarily override the AI pH-stat controller.
2. Flood the sparger with pure CO₂ until the reactor pH drops to 4.5. Hold for exactly 4 hours.
3. **Biological Mechanism:** *Chlorella* cells possess rigid cell walls and survive this extreme carbonic acid spike. Complex, soft-bodied freshwater zooplankton predators will undergo osmotic stress, lyse (rupture), and die.
4. Return to normal pH 6.8 operations. Culture recovers to exponential growth within 48 hours.