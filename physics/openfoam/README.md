# 🌊 OpenFOAM Physics Simulation

The `/physics/openfoam/` directory houses the computational fluid dynamics (CFD) parameters that validated the design of the CV-PBR-V1 bioreactor.

## 🌀 Scope
The CFD simulation modeled a full 1,000-liter geometry utilizing `snappyHexMeshDict` and `reactingMultiphaseEulerFoam` solving equations for the MUSIG bubble size distribution, the k-ω SST turbulence modeling, and the Han ODE biokinetics model.

## ✅ Biological Constraints Passed
These simulations specifically sought to validate **OQ-5** the critical shear stress limit for *Chlorella vulgaris*:

1. **Max Shear Stress:** Simulation resolved $G_{max} \approx 1,240 \text{ s}^{-1}$ in the vortex core—well below the critical $3,000 \text{ s}^{-1}$ limit, confirming no cellular lysis.
2. **Phase Lock Sync:** The correlation between the RPM vortex angular velocity and the LED strobe duty cycle ($50Hz$ vs photon penetration) was documented.

See `VALIDATION_REPORT.md` in this directory for the deep dive on the mathematical passing thresholds.
