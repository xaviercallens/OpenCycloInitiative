CYCLOTWIN-SIM V1.0: DIGITAL TWIN IMPLEMENTATION GUIDE

**OpenCyclo Initiative | Technical Engineering Manual**

**Target OS:** Ubuntu 24.04 LTS (Native or WSL2)

**Compute Requirements:** Multi-core CPU (OpenFOAM) + NVIDIA RTX 3080/4080 or higher (Modulus PINN)

This document provides the step-by-step implementation guide to build **CycloTwin-Sim**, the digital twin of the OpenCyclo Bioreactor. By coupling high-fidelity computational fluid dynamics (CFD), Lagrangian biokinetics, and Physics-Informed Neural Networks (PINNs), engineers can test hardware geometries and AI control scripts in a deterministic, zero-risk virtual environment before physical construction.

---

## 🛠️ 1. THE OPEN-SOURCE SOFTWARE STACK

To avoid proprietary lock-in, the entire simulation stack relies on permissive open-source frameworks:

| Module | Open-Source Framework | Function in the Digital Twin |
| --- | --- | --- |
| **Fluid & Optics Solver** | **[OpenFOAM v2312+](https://www.openfoam.com/)** | Solves Navier-Stokes, Multiphase tracking, and Radiative Transfer offline. |
| **Real-Time Physics AI** | **[NVIDIA Modulus](https://developer.nvidia.com/modulus)** | Trains PINNs to compress OpenFOAM physics into a real-time (millisecond) engine. |
| **Biokinetic Coupling** | **[preCICE v3.x](https://precice.org/)** | Couples the fluid solver to external Python ODE scripts for cellular growth tracking. |
| **Middleware / SITL** | **[ROS 2 Jazzy Jalisco](https://docs.ros.org/)** | Message broker spoofing hardware GPIO/I2C for the Python Control OS. |
| **Synthetic Vision** | **[Blender 4.x (Python API)](https://www.blender.org/)** | Renders fluid `.vdb` data into photorealistic 1080p video for the YOLOv8 AI. |

---

## 🌊 2. PHASE 1: HIGH-FIDELITY CFD SETUP (OPENFOAM)

*Goal: Establish the absolute ground-truth physics for multiphase hydrodynamics (water + CO₂ nanobubbles) and the 3D photonic field (LEDs).*

### **Step 2.1: Mesh Generation (`snappyHexMesh`)**

1. Export the internal fluid volume of the 1,000L vessel CAD as an STL file (`vessel_fluid.stl`).
2. Define the background cylindrical mesh using `blockMesh`.
3. Run `snappyHexMesh` with a 5-layer prism insertion at the walls.
* **Engineering Constraint:** Ensure the dimensionless wall distance () is strictly  at the outer Polycarbonate wall. This is mandatory for the  turbulence model to accurately resolve the high-shear boundary layer where the "Flashing Light Effect" occurs.



### **Step 2.2: Multiphase Physics (`reactingMultiphaseEulerFoam`)**

Set up the `0/` directory and `constant/phaseProperties`:

* **Boundary - Inlet (`U.water`):** Set a fixed volume flow (e.g., ) at the tangential port to induce the Rankine vortex.
* **Boundary - Sparger (`U.gas`):** Set a mass flux equating to  (Volumes of gas per Volume of liquid per min).
* **Bubble Size & Drag:** Use the **MUSIG (Multiple Size Group)** model, initializing bubbles at . Use the Schiller-Naumann drag model and Tomiyama lift model (crucial for predicting if bubbles are sucked into the vortex core or pushed to the walls).
* **Interphase Mass Transfer:** Define the **Higbie Penetration Theory** to calculate  (the rate of CO₂ dissolving into water based on turbulent eddy dissipation):
$$ k_L = 2 \sqrt{\frac{D_c}{\pi t_e}} $$

### **Step 2.3: Radiative Transfer Equation (RTE)**

In `constant/radiationProperties`:

* Select the **fvDOM** (Finite Volume Discrete Ordinates Method) solver.
* Define the 4 glass light guides as emission boundaries ().
* Map the absorption coefficient () to the local biomass scalar (). As  increases (water gets greener), light penetration depth exponentially decays according to the Beer-Lambert Law: .

---

## 🦠 3. PHASE 2: BIOKINETIC LAGRANGIAN TRACKING

*Goal: Mathematically prove the "Flashing Light Effect" by tracking virtual algae cells through the vortex.*

### **Step 3.1: Injecting Lagrangian Particles**

Using OpenFOAM's `kinematicCloud` library, inject 100,000 massless tracer particles representing algal cells. As they sweep through the Eulerian fluid mesh, they log the exact Light Intensity () they experience at every millisecond step: .

### **Step 3.2: The Han Photosynthetic ODE Model**

Use **preCICE** to pipe the  histories to a Python script evaluating the **Han Model (2001)**. Each cell exists in three Plastoquinone states:

* : Open state (ready to absorb photon).
* : Closed state (processing photon, needs dark time).
* : Inhibited state (damaged by too much light/photoinhibition).

$$ \frac{dx_1}{dt} = - \sigma I(t) x_1 + \frac{x_2}{\tau} $$
$$ \frac{dx_2}{dt} = \sigma I(t) x_1 - \frac{x_2}{\tau} - k_d I(t) x_2 + k_r x_3 $$

* *Implementation Logic:* If the simulated VFD pump speed matches the LED PWM pulsing frequency perfectly,  will smoothly process photons into biomass without spilling into  (damage). The integral of this ODE outputs the total Biomass Growth Rate ().

---

## 🧠 4. PHASE 3: REAL-TIME SURROGATE MODEL (NVIDIA MODULUS)

*Goal: OpenFOAM takes 3 days to simulate 1 minute. We need it to run in 10 milliseconds to test our AI.*

### **Step 4.1: Data Generation & Formatting**

Run the OpenFOAM solver across a Latin Hypercube sampling of inputs to generate a training dataset:

* Pump Frequency:  to 
* LED PWM Duty Cycle:  to 
* CO₂ Valve State: Open/Closed

### **Step 4.2: PINN Architecture Configuration**

In NVIDIA Modulus, define a continuous spatial-temporal neural network (specifically a **Fourier Neural Operator - FNO**):

* **Inputs:** 
* **Outputs:** 
* **Loss Function:** Combine the Mean Squared Error (MSE) of the OpenFOAM training data with the **physics residuals of the Navier-Stokes continuity equations**. This ensures the AI doesn't hallucinate physically impossible fluid motions.

### **Step 4.3: Export as TensorRT**

Once trained, export the Modulus model as an optimized ONNX/TensorRT engine. This allows the 3D physics simulation to run at  on the edge device during SITL testing.

---

## 🔌 5. PHASE 4: SOFTWARE-IN-THE-LOOP (SITL) & SYNTHETIC VISION

*Goal: Connect the physical OpenCyclo Python OS to the virtual reactor, fooling it into thinking it is controlling physical hardware.*

### **Step 5.1: ROS 2 Hardware Mocking (I2C/GPIO)**

1. Launch a ROS 2 Jazzy node (`/virtual_hardware_bridge`).
2. When the OpenCyclo OS calls the Python `RPi.GPIO` library to open the CO₂ valve, intercept this call using a custom wrapper and publish a ROS 2 message: `topic: /cmd_co2_valve, data: True`.
3. The PINN (running in real-time) subscribes to this topic, simulates the pH dropping, and publishes the new pH back to `/sensor_ph`. The OpenCyclo OS reads this, believing it just read a physical Atlas Scientific I2C probe.

### **Step 5.2: Blender VDB Synthetic Rendering**

The OpenCyclo OS uses YOLOv8 to estimate density and detect predators. We must feed it fake video.

1. Write a Python script using the `pyopenvdb` library to export the PINN's 3D scalar fields for Biomass and Bubbles as an OpenVDB (`.vdb`) file sequence.
2. Import the VDB sequence into **Blender 4.x** via its Python API.
3. Assign a Principled Volume shader. Link the VDB "Density" attribute to scattering/absorption, mapping the color to the deep emerald of *Chlorella*.
4. *Domain Randomization:* Write a Blender Python script to randomly inject 3D models of *Brachionus* rotifers tumbling through the volume to train the biosecurity AI.
5. Render the camera viewport headlessly using EEVEE (real-time).

### **Step 5.3: The Video Loopback (`v4l2loopback`)**

Pipe the real-time Blender render directly to a virtual webcam on your Linux host:

```bash
sudo modprobe v4l2loopback devices=1 video_nr=0 exclusive_caps=1
ffmpeg -f rawvideo -pix_fmt rgb24 -s 1920x1080 -i pipe:0 -f v4l2 /dev/video0

```

Start the OpenCyclo `vision_density.py` script. It will open `/dev/video0`, view the photorealistic synthetic rendering of the fluid, estimate the density, and hunt for rotifers exactly as it would on the real machine.

---

SCIENTIFIC REFERENCES & VALIDATION ANCHORS

To ensure mathematical rigor, the simulator implementation is anchored in the following academic benchmarks:

1. **Fluid & Bubble Dynamics:**
* *Jakobsen, H. A. (2014). Chemical Reactor Modeling: Multiphase Reactive Flows.* (Standard text for Eulerian-Eulerian multiphase coupling).
* *Ishii, M., & Hibiki, T. (2011). Thermo-fluid Dynamics of Two-Phase Flow.* (MUSIG model equations).


2. **Mass Transfer in Vortexes:**
* *Higbie, R. (1935). The rate of absorption of a pure gas into a still liquid during short periods of exposure. AIChE Journal.* (Penetration theory used for the  nanobubble calibration).


3. **Photosynthetic Biokinetics (The Flashing Light Effect):**
* *Han, B. P. (2001). Photosynthesis-irradiance response at physiological level: a mechanistic model. Journal of Theoretical Biology, 213(2).* (Defines the 3-state ODE used in Phase 2).


4. **Radiative Transfer in Algae:**
* *Pilon, L., et al. (2011). Radiation transfer in photobioreactors. Applied Energy.* (Defines the absorption and scattering cross-sections for *Chlorella vulgaris* needed for `fvDOM`).


5. **Physics-Informed Neural Networks:**
* *Raissi, M., et al. (2019). Physics-informed neural networks. Journal of Computational Physics.* (The foundational math behind NVIDIA Modulus).