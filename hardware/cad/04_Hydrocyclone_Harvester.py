"""
OpenCyclo Initiative — Hydrocyclone Harvester
=============================================

Generates 04_Hydrocyclone_Harvester.stl CAD file.

Specifications:
- Rietema proportions
- Main cylinder: 100 mm OQ-1 fulfilled
- Underflow apex: 15 mm
- Overflow vortex finder: 35 mm
- SLA / FDM ready
"""

import cadquery as cq

# Rietema Proportions based on main cylinder Dc
Dc = 100.0          # Main cylinder diameter
Di = Dc * 0.28      # Inlet diameter
Do = Dc * 0.34      # Overflow diameter
Du = Dc * 0.15          # Underflow apex diameter
L1 = Dc * 0.4       # Vortex finder length
L2 = Dc * 1.0       # Cylinder body length
L3 = Dc * 4.0       # Conical section length

WALL = 3.0          # Uniform wall thickness for FDM

def build_hydrocyclone():
    # Body
    cylinder = cq.Workplane("XY").circle(Dc/2.0).extrude(L2)
    cone = (cq.Workplane("XY").workplane(offset=-L3)
            .circle(Du/2.0+WALL)
            .workplane(offset=L3)
            .circle(Dc/2.0)
            .loft(combine=True))
    
    body = cylinder.union(cone)
    
    # Internal cutout (shell)
    # Easiest way is to union the interior positives, then cut them from the solid body.
    cut_cyl = cq.Workplane("XY").circle((Dc/2.0)-WALL).extrude(L2)
    cut_cone = (cq.Workplane("XY").workplane(offset=-L3)
                .circle(Du/2.0)
                .workplane(offset=L3)
                .circle((Dc/2.0)-WALL)
                .loft(combine=True))
    
    interior = cut_cyl.union(cut_cone)
    
    # Inlet
    inlet_plane = cq.Workplane("XY").workplane(offset=L2 - (Di/2) - WALL)
    inlet = (inlet_plane
             .center((Dc/2.0)-(Di/2.0)-1.0, 0)
             .circle(Di/2.0 + WALL)
             .extrude(60.0))
    cut_inlet = (inlet_plane
                 .center((Dc/2.0)-(Di/2.0)-1.0, 0)
                 .circle(Di/2.0)
                 .extrude(60.0))
                 
    # Overflow
    overflow_finder = cq.Workplane("XY").workplane(offset=L2).circle(Do/2.0 + WALL).extrude(40.0)
    cut_overflow = cq.Workplane("XY").workplane(offset=L2-L1).circle(Do/2.0).extrude(40.0+L1)
    
    # Combine positives
    shell = body.union(inlet).union(overflow_finder)
    # Combine negatives
    voids = interior.union(cut_inlet).union(cut_overflow)
    
    return shell.cut(voids)

if __name__ == "__main__":
    print("Generating 04_Hydrocyclone_Harvester.stl...")
    result = build_hydrocyclone()
    cq.exporters.export(result, "04_Hydrocyclone_Harvester.stl")
    print("Export complete.")

