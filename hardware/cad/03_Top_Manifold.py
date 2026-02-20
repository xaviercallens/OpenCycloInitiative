"""
OpenCyclo Initiative — Top Light & Sensor Manifold
==================================================

Generates 03_Top_Manifold.step CAD file.

Specifications:
- Material: CNC-milled Delrin (POM-C)
- 4x Borosilicate light guide boreholes with O-ring grooves
- 3x PG13.5 threaded sensor ports
- Central exhaust port
- Media top-up threaded port
"""

import cadquery as cq

# Dimensions
MANIFOLD_OD = 310.0
MANIFOLD_THICKNESS = 40.0
LIGHT_GUIDE_DIA = 30.0   # OD of borosilicate tubes
SENSOR_PORT_DIA = 13.5   # PG13.5
EXHAUST_DIA = 50.8
TOP_UP_DIA = 25.4

def build_manifold():
    manifold = cq.Workplane("XY").circle(MANIFOLD_OD/2.0).extrude(MANIFOLD_THICKNESS)

    # Central exhaust
    manifold = manifold.faces(">Z").workplane().circle(EXHAUST_DIA/2.0).cutThruAll()

    # Top-up port slightly offset
    manifold = manifold.faces(">Z").workplane().center(EXHAUST_DIA + 20, 0).circle(TOP_UP_DIA/2.0).cutThruAll()

    # 4 Light guides
    for angle in [0, 90, 180, 270]:
        manifold = (manifold.faces(">Z").workplane().polarArray(MANIFOLD_OD/3.0, angle, 360, 1)
                    .circle(LIGHT_GUIDE_DIA/2.0).cutThruAll())

    # 3 PG13.5 ports
    for angle in [45, 135, 225]:
        manifold = (manifold.faces(">Z").workplane().polarArray(MANIFOLD_OD/3.5, angle, 360, 1)
                    .circle(SENSOR_PORT_DIA/2.0).cutThruAll())

    return manifold

if __name__ == "__main__":
    print("Generating 03_Top_Manifold.step...")
    result = build_manifold()
    cq.exporters.export(result, "03_Top_Manifold.step")
    print("Export complete.")

