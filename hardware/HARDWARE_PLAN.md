# 🛠️ OpenCyclo Initiative — Hardware Fabrication Plan

> **Version:** 1.0.0
> **License:** CERN-OHL-S v2 (Open Hardware License - Strongly Reciprocal)
> **Goal:** Build the CV-PBR-V1 (Cyclo-Vortex Planetary Bioreactor)

This document is the master playbook for fabricating, assembling, and commissioning the physical reactor. **All CAD files (.step and .stl) are provided in `hardware/cad/` alongside a native FreeCAD assembly macro (`Assemble_OpenCyclo.FCMacro`).**

---

## 🏗️ 1. Master Strategy & BOM

The hardware is designed entirely for decentralized makerspaces and Open Source Ecology nodes. The Bill of Materials (BOM) is located at `hardware/cad/BOM.csv`.

**The Three Tiers of Fabrication:**
1. **COTS (Commercial Off-The-Shelf):** Aluminum extrusions, stepper motors, silicone tubing, 24V PSU.
2. **CNC / Subtractive:** Top manifold, Stainless Steel Hydro-Base cone (or high-heat PETG if 3D printed).
3. **SLA / Additive:** Hydrocyclone Harvester (must be SLA resin to guarantee ultra-smooth internal surfaces for the Rietema proportions to work efficiently).

---

## 🗜️ 2. Sub-Assembly Breakdown

### 2.1 The Frame (`CV_SMU1000_Master`)
* **Material:** 80/20 T-Slot Aluminum Extrusion (2020 Series).
* **Notes:** Assemble the vertical uprights first to form a perfect square, establishing the bounding box. The frame must be perfectly plumb to ensure the hydro-base does not list, causing catastrophic vortex wobble.

### 2.2 The Growth Chamber (`01_Polycarbonate_Vessel`)
* **Material:** Extruded Polycarbonate Tube (do NOT substitute with Acrylic/PMMA due to catastrophic failure under pressurization and inferior UV transmission).
* **Notes:** The endpoints of the cylinder must be faced on an end mill or lathe to ensure perfect flatness for the EPDM gasket seal.

### 2.3 The Hydro-Base (`02_Hydro_Base_60deg`)
* **Material:** 316L Stainless Steel (or alternatively machined Delrin).
* **Crucial:** The tangential inlet is angled precisely to generate the Rankine Vortex without causing cavitation. **Do not modify the inlet geometry in the CAD file.** If the $k_L a$ drops due to improper shear stress, the biokinetics fail. Connect this to the main 24V brushless centrifugal pump.

### 2.4 The Top Manifold (`03_Top_Manifold`)
* **Material:** POM-C (Delrin). Used for its excellent machinability and thread retention.
* **Notes:** This cap houses the exhaust port, the array of sensors (pH, Temp), and the photon emitters. CNC tap the sensor ports to standard NPT/BSP threads based on your specific probe sizing. Use PTFE tape for sealing.

### 2.5 The Harvester (`04_Hydrocyclone_Harvester`)
* **Material:** SLA Photopolymer Resin.
* **Notes:** This is the physical separator that concentrates the *Chlorella* paste and returns clarified water to the reactor. FDM printing will leave layer lines that destroy the laminar fluid film required for cyclonic separation. SLA printing at $0.05$ layer height is strictly required.

---

## 🔧 3. Electronics & Wiring Plan

1. **The Brain:** Jetson Nano or Raspberry Pi 5 runs `main_loop.py`.
2. **Motor Control:** Connect the VFD (Variable Frequency Drive) or 24V Brushless Pump ESC directly to the Pi's PWM GPIO output via a logic level shifter.
3. **Pneumatics:** Connect the 24V 3-way motorized ball valve (for harvest automation) and the CO₂ solenoid to a MOSFET breakout board driven by the Pi.
4. **Spectroscopy / Vision:** Mount the OpenCV camera rigidly to the frame pointing *inward* through the polycarbonate tube exactly 4 inches above the base cone. Secure the backlight LED array opposite the camera.

---

## 🧩 4. Assembly & Startup (FreeCAD)

If you have installed FreeCAD, follow these instructions to view the digital twin before ordering materials:

```text
1. Open FreeCAD on your system.
2. Navigate to View -> Panels -> Python console (if not visible).
3. Go to Macro -> Macros... -> Choose 'Assemble_OpenCyclo.FCMacro'.
4. Click Execute.
```

The system will automatically load all 5 components, snap them into position, and apply clear polycarbonate and gray-metal textures so you can visually verify the fit tolerances.

---

## 🧪 5. Calibration Hookup

Once assembled, do not immediately inoculate with algae.
Run the OpenCyclo OS using `python3 software/opencyclo_os/calibration.py`. This script will pump distilled water through the system, pulse the LEDs, and test the PID controllers against a static baseline to ensure there are no plumbing leaks and no thermal runaway issues.
