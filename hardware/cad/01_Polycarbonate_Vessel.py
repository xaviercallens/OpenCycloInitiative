"""
OpenCyclo Initiative — Main PBR Cylinder
========================================

Generates the 01_Polycarbonate_Vessel.step CAD file.

Specifications:
- Material: UV-stabilized Polycarbonate
- Outer Diameter (OD): 300 mm
- Wall Thickness: 5 mm
- Length: 1200 mm 
- Ends: Flat machined for EPDM gasket mating
"""

import cadquery as cq

# Parameters (Addresses OQ-1 dimensional gaps)
OD = 300.0          # mm
WALL_THICKNESS = 5.0 # mm
ID = OD - (2 * WALL_THICKNESS)
LENGTH = 1200.0     # mm

def build_vessel():
    # Create the main cylinder
    vessel = (cq.Workplane("XY")
              .circle(OD / 2.0)
              .circle(ID / 2.0)
              .extrude(LENGTH))
    
    # Add chamfers at the ends for O-ring/gasket seating
    # Selecting the outer edges of the top and bottom faces
    edges = vessel.edges("%CIRCLE")
    vessel = vessel.chamfer(0.5, edges)

    return vessel

if __name__ == "__main__":
    print("Generating 01_Polycarbonate_Vessel.step...")
    result = build_vessel()
    cq.exporters.export(result, "01_Polycarbonate_Vessel.step")
    print("Export complete.")

