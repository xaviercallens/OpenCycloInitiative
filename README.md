# 🌿 OpenCyclo Initiative — CV-PBR-V1

**Open-Source Cyclo-Vortex Algae Photobioreactor System**

[![License: CERN-OHL-S](https://img.shields.io/badge/Hardware-CERN--OHL--S-blue)](https://ohwr.org/cern_ohl_s_v2.txt)
[![License: MIT](https://img.shields.io/badge/Software-MIT-green)](LICENSE-SOFTWARE)
[![License: OpenMTA](https://img.shields.io/badge/Wetware-OpenMTA-orange)](https://www.addgene.org/open-mta/)

> A fully open-source, AI-driven 1,000-Liter Standard Modular Unit (SMU-1000) for continuous, high-density algae cultivation using Cyclo-Vortex hydrodynamics and nanobubble gas delivery.

---

## 📁 Repository Structure

```
OpenCycloInitiative/CV-PBR-V1/
├── docs/                          # Technical specifications & documentation
│   └── technical_specifications.md
├── hardware/                      # CAD & mechanical engineering files
│   └── cad/
│       ├── README.md
│       ├── CV_SMU1000_Master.step         # Master assembly (1000L SMU)
│       ├── 01_Polycarbonate_Vessel.step   # Main PBR cylinder
│       ├── 02_Hydro_Base_60deg.step       # Cyclo-Vortex base cone (316L SS)
│       ├── 03_Top_Manifold.step           # Top light & sensor manifold
│       └── 04_Hydrocyclone_Harvester.stl  # 3D-printed hydrocyclone
├── software/                      # Python control system (OpenCyclo OS)
│   └── opencyclo_os/
│       ├── main_loop.py           # Core async orchestrator / state-machine
│       ├── vision_density.py      # YOLOv8 computer vision soft sensor
│       ├── ph_stat_co2.py         # Carbon dosing PID controller
│       ├── led_pwm_sync.py        # Flashing light effect sync
│       ├── config.py              # System-wide configuration & constants
│       └── requirements.txt       # Python dependencies
├── physics/                       # CFD simulation (OpenFOAM v2312)
│   └── openfoam/
│       ├── README.md
│       ├── system/
│       │   ├── snappyHexMeshDict  # Mesh generation config
│       │   ├── fvSolution
│       │   └── fvSchemes
│       ├── constant/
│       │   └── phaseProperties    # Multiphase fluid properties
│       └── 0/                     # Boundary conditions
│           ├── U.water
│           ├── U.gas
│           └── p_rgh
└── wetware/                       # Biological SOPs & protocols
    └── protocols/
        ├── SOP-101_Media_Formulation.md
        ├── SOP-102_Strain_Inoculation.md
        ├── SOP-103_Turbidostat_Harvesting.md
        └── SOP-104_Contamination_Biosecurity.md
```

---

## 🚀 Quick Start

### Hardware
See [`hardware/cad/README.md`](hardware/cad/README.md) for machining and 3D printing instructions.

### Software (Python Control OS)
```bash
# Install dependencies (Python 3.10+, on Jetson Nano or Raspberry Pi 5)
pip install -r software/opencyclo_os/requirements.txt

# Launch the control daemon
python software/opencyclo_os/main_loop.py
```

### CFD Simulation
```bash
# Requires OpenFOAM v2312
cd physics/openfoam
blockMesh && snappyHexMesh -overwrite
reactingMultiphaseEulerFoam
paraFoam  # Visualize results
```

---

## ⚡ Key Technologies

| Layer | Technology | Purpose |
|---|---|---|
| **Hardware** | 316L SS + UV-PC + Delrin | Biocompatible, corrosion-resistant structure |
| **Hydrodynamics** | Rankine Vortex (Cyclonic) | Zero dead-zones, passive cell suspension |
| **Gas Delivery** | Nanobubble Sparger | 100% CO₂ absorption efficiency |
| **Harvesting** | Hydrocyclone (Rietema) | Passive centrifugal concentration |
| **Control OS** | Python `asyncio` on Jetson Nano | Edge AI, real-time PID control |
| **Soft Sensor** | YOLOv8 INT8 + OpenCV | Non-invasive biomass density estimation |
| **CFD** | OpenFOAM `reactingMultiphaseEulerFoam` | Fluid mechanics validation |
| **Biology** | *Chlorella vulgaris* UTEX 2714 | High shear-tolerant production strain |

---

## 📜 Licensing

- **Hardware** (CAD files, schematics): [CERN Open Hardware Licence v2 - Strongly Reciprocal (CERN-OHL-S)](https://ohwr.org/cern_ohl_s_v2.txt)
- **Software** (Python scripts, firmware): [MIT License](LICENSE-SOFTWARE)
- **Wetware** (Biological protocols, SOPs): [Open Material Transfer Agreement (OpenMTA)](https://www.addgene.org/open-mta/)

---

## 🤝 Contributing

This project is open to engineers, microbiologists, software developers, and sustainability advocates. Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before submitting pull requests.

---

*Part of the OpenCyclo Initiative — Democratizing algae biotechnology for food, fuel, and carbon capture.*
