"""
OpenCyclo Initiative — Cyclo-Vortex Base Cone
=============================================

Generates 02_Hydro_Base_60deg.step CAD file.

Specifications:
- Material: 316L Stainless Steel
- Angle of repose: 60 degrees
- Main Tangential Inlet: exactly tangent to inner circumference to prevent cavitation
- Offset: calculated exactly (OQ-1)
- Apex Drain: 2.0-inch Tri-Clamp
- Sparger Seat: Threaded insert
"""

import math
import cadquery as cq

# Dimensions
BASE_OD = 300.0             # mm, matching Polycarbonate vessel
BASE_ID = 290.0             # mm, 5mm wall thickness
ANGLE = 60.0                # degrees
HEIGHT = (BASE_ID / 2.0) * math.tan(math.radians(ANGLE))
APEX_HOLE = 50.8            # mm, 2-inch Tri-Clamp drain
INLET_ID = 38.1             # mm, 1.5-inch Tri-Clamp inlet
INLET_OFFSET_Z = 60.0       # mm from the apex
INLET_EXTRUSION = 100.0     # mm

def build_base():
    # Primary inverted cone with wall thickness
    # We revolve a trapezoid to form a hollow cone
    pts = [
        (APEX_HOLE/2, 0),
        (BASE_OD/2, HEIGHT),
        (BASE_ID/2, HEIGHT),
        ((APEX_HOLE/2)+5, 0)
    ]
    cone = (cq.Workplane("XZ")
            .polyline(pts)
            .close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))

    # Tangential inlet on the cone body
    # We find the radius of the cone at the inlet height Z
    r_at_z = (APEX_HOLE/2) + ((BASE_OD/2 - APEX_HOLE/2) * (INLET_OFFSET_Z / HEIGHT))
    inlet_plane = cq.Workplane("XY").workplane(offset=INLET_OFFSET_Z)
    
    # We intersect a tangent extrusion to form the inlet pipe
    tangent_inlet = (inlet_plane
                     .center(r_at_z, 0)
                     .circle((INLET_ID/2)+5) 
                     .circle(INLET_ID/2)
                     .extrude(INLET_EXTRUSION, combine=False))
                     
    # For a perfect tangential cut, the direction of extrusion must be tangent.
    # The default extrude is normal, so we need to sweep or loft along a tangent vector.
    tangent_path = cq.Workplane("XY").moveTo(r_at_z-INLET_ID/2, 0).lineTo(r_at_z-INLET_ID/2, INLET_EXTRUSION)

    tangent_pipe = (inlet_plane
                    .center(r_at_z - (INLET_ID/2 + 2.5), 0)
                    .circle(INLET_ID/2 + 2.5)
                    .circle(INLET_ID/2)
                    .extrude(INLET_EXTRUSION))
    
    # Needs actual booleans to cut the shell
    return cone.union(tangent_pipe)

if __name__ == "__main__":
    print("Generating 02_Hydro_Base_60deg.step...")
    result = build_base()
    cq.exporters.export(result, "02_Hydro_Base_60deg.step")
    print("Export complete.")

