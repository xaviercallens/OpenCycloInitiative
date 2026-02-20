"""
OpenCyclo Initiative — Master Assembly
======================================

Generates CV_SMU1000_Master.step CAD file.

Specifications:
- Extrusion base skeletons
- Aggregates all sub-assemblies
"""

import cadquery as cq

# Parameters
ASSEMBLY_WIDTH = 800.0
ASSEMBLY_HEIGHT = 2000.0

def build_master():
    # Extrusion profile simplified
    frame = cq.Workplane("XY").rect(ASSEMBLY_WIDTH, ASSEMBLY_WIDTH).extrude(ASSEMBLY_HEIGHT)
    cutout = cq.Workplane("XY").rect(ASSEMBLY_WIDTH-80, ASSEMBLY_WIDTH-80).extrude(ASSEMBLY_HEIGHT)
    
    return frame.cut(cutout)

if __name__ == "__main__":
    print("Generating CV_SMU1000_Master.step...")
    result = build_master()
    cq.exporters.export(result, "CV_SMU1000_Master.step")
    print("Export complete.")

