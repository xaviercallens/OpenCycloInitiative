OPENCYCLO INITIATIVE: DIGITAL TWIN SPECIFICATION

**Project Code:** `CycloTwin-Sim` (V1.0 Architecture Specification)

**Core Frameworks:** OpenFOAM, NVIDIA Modulus (PINNs), ROS 2, Blender/Godot

**License:** GNU GPLv3 / MIT

To move from a 15-Liter garage prototype to a globally scalable 1,000-Liter industrial array, physical trial-and-error is too slow and expensive. The **OpenCyclo Digital Twin (CycloTwin)** is a fully integrated, multi-physics simulation framework. It allows engineers to digitally test impeller designs, LED placements, and AI control scripts in a deterministic, zero-risk virtual environment before cutting a single piece of polycarbonate.

Leveraging the 2026 state-of-the-art in academic open-source physics engines, the simulator tightly couples Eulerian fluid dynamics, Lagrangian particle tracking, radiative transfer, and Software-in-the-Loop (SITL) control.

---

## 🏗️ 1. MACRO ARCHITECTURE: THE HYBRID CO-SIMULATION

Running a continuous multi-physics simulation of a 1,000-liter multiphase bioreactor is computationally immense. Therefore, CycloTwin relies on a hybrid **Co-Simulation Architecture**:

1. **The High-Fidelity Engine (Offline/Design):** Uses rigorously validated Computational Fluid Dynamics (CFD) to solve the Navier-Stokes equations. Used for mechanical design, geometry validation, and establishing baseline physics.
2. **The Real-Time Surrogate Engine (Online/Control):** Uses Physics-Informed Neural Networks (PINNs) trained on the offline data. This compresses days of computing into millisecond predictions, allowing the real OpenCyclo Python OS to plug into the simulator (Software-in-the-Loop) as if it were physical hardware.

---

## 🌊 2. MODULE 1: MULTIPHASE HYDRODYNAMICS (The Fluid Engine)

*The core physics engine handling the Rankine vortex, nanobubble dispersion, and shear stress.*

* **Framework:** **OpenFOAM (v2312 or later)** — The academic standard for open-source CFD.
* **Primary Solver:** `reactingMultiphaseEulerFoam`.
* **Physics Modalities:**
* **Turbulence:**  SST (Shear Stress Transport) to accurately resolve the boundary layer near the polycarbonate walls and the cyclonic core.
* **Bubble Dynamics:** Implements the *Population Balance Equation (PBE)* via the MUltiple SIze Group (MUSIG) model to track the coalescence and breakup of the  CO₂ nanobubbles.
* **Mass Transfer:** Uses the *Higbie Penetration Theory* to calculate the Volumetric Mass Transfer Coefficient () as CO₂ dissolves into the continuous liquid phase.


* **Critical Output:** The solver outputs the 3D scalar field of the turbulent shear rate (). If  in any mesh cell, the simulator flags a "Cell Lysis Event" (biological death by mechanical shredding).

---

## ☀️ 3. MODULE 2: RADIATIVE TRANSFER & OPTICS (The Photonic Field)

*Simulating the volumetric penetration of the 680nm/450nm LEDs into a dense, green, bubbly fluid.*

* **Framework:** OpenFOAM's **fvDOM** (Finite Volume Discrete Ordinates Method).
* **Physics:** Solves the Radiative Transfer Equation (RTE) for an absorbing, emitting, and scattering medium in 3D space.
* **Dynamic Attenuation (Beer-Lambert):** The absorption coefficient () and scattering phase functions are dynamically coupled to the local biomass concentration () and bubble void fraction ().
* *Equation Coupling:* 
* As the virtual algae grow, the fluid becomes darker, physically shrinking the illuminated zone in real-time.



---

## 🦠 4. MODULE 3: LAGRANGIAN BIOKINETICS (The Cellular Engine)

*Algae do not experience average light; they experience a chaotic, flashing light history as they swirl.*

* **Framework:** OpenFOAM Lagrangian Particle Tracking (`kinematicCloud`) coupled with Python via **preCICE** (an open-source multi-physics coupling library).
* **Mechanism:** 100,000 massless "Lagrangian tracer particles" (representing algal cells) are injected into the Eulerian fluid vortex.
* **Light Integration:** As each particle travels, it records the exact photon flux () it receives at every millisecond.
* **Photosynthetic State Machine (The Han Model):** Each particle runs an ODE-based 3-state photosynthetic factory model:
1. *Resting State:* Ready to absorb a photon.
2. *Active State:* Photon absorbed, processing chemical energy (requires dark time).
3. *Inhibited State:* Hit by too many photons, RuBisCO enzyme damaged.


* **Result:** This is the *only mathematical way* to prove whether the VFD pump speed perfectly synchronizes with the LED PWM pulse rate to achieve the highly efficient **Flashing Light Effect (FLE)**.

---

## 🧠 5. MODULE 4: REAL-TIME REDUCED ORDER MODEL (PINNs)

*OpenFOAM is too computationally heavy to run real-time AI training. We bridge this with PINNs.*

* **Framework:** **NVIDIA Modulus** (Open-source PINN framework) or **DeepXDE**.
* **Mechanism:** We generate thousands of OpenFOAM snapshots under various pump speeds, LED intensities, and bubble rates. We train a Physics-Informed Neural Network to learn the *latent space* of the reactor's physics, constrained by the Navier-Stokes equations.
* **Output:** The PINN runs at >60 FPS on a standard consumer GPU or Edge device. Given a VFD pump frequency and gas valve state, it instantly predicts the 3D fields for pH, dissolved CO₂, and biomass density without solving the differential equations from scratch.

---

## 🔌 6. MODULE 5: SOFTWARE-IN-THE-LOOP (SITL) & SYNTHETIC VISION

*How the OpenCyclo Python OS thinks the Simulator is a physical reactor.*

* **Middleware Bridge:** **ROS 2 (Humble/Jazzy)** + **MQTT Broker**.
* **Hardware Mocking:**
* The OpenCyclo OS `ph_stat_co2.py` script sends a GPIO signal to open the CO₂ valve.
* A virtual I2C-to-ROS bridge intercepts this and tells the PINN simulator: `Valve = OPEN`.
* The PINN simulates the CO₂ dissolving, calculates the new pH, and sends a virtual I2C signal back to the OpenCyclo OS: `pH = 6.8`.


* **Synthetic Computer Vision:**
* **Engine:** **Blender (Python API) / Godot 4**.
* The fluid dynamics and biomass density scalars from the PINN are exported to Blender/Godot as `.VDB` files.
* The rendering engine generates a photorealistic 3D rendering of the green swirling vortex (including simulated bubbles, LED lighting, and synthetic rotifer contaminants).
* This synthetic video feed is piped to `/dev/video0` (Virtual Webcam).
* The OpenCyclo OS `vision_density.py` (YOLOv8) analyzes this synthetic video feed, completely unaware that it is looking at a video game engine rather than a physical reactor.



---

## 🚀 7. DEPLOYMENT & USAGE WORKFLOW

The CycloTwin Simulator is distributed as a set of Docker containers (`docker-compose.yml`) to ensure absolute environment parity across global research nodes.

### **The Container Stack:**

1. **`oc-cfd-core`**: The OpenFOAM volume (requires high CPU core count for offline solving/meshing via `snappyHexMesh`).
2. **`oc-pinn-rt`**: The real-time PyTorch/Modulus physics engine (requires NVIDIA GPU/CUDA).
3. **`oc-render-engine`**: Godot/Blender headless instance for generating the synthetic camera feed.
4. **`oc-sil-bridge`**: The ROS2/MQTT message broker translating physics data to virtual hardware pins (I2C/GPIO).

### **Example Use-Case: Tuning a New Industrial AI Algorithm**

1. An engineer writes a new Reinforcement Learning (RL) algorithm to optimize the LED pulsing frequency for energy savings.
2. They boot up the CycloTwin SITL stack.
3. The RL algorithm takes control of the virtual reactor. Over a weekend, it runs 5,000 simulated days of algae growth, adjusting the virtual VFD pump and LED PWM thousands of times.
4. It discovers that pulsing the LEDs at exactly  while the pump runs at  yields a 12% increase in biomass while cutting electrical draw by 20%.
5. On Monday, that exact Python script is pushed via OTA update to the physical 1,000-Liter tanks in the field, executing flawlessly on Day 1.