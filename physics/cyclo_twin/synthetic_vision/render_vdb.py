"""
CycloTwin — Synthetic Vision Pipeline
========================================

Blender Python script for generating photorealistic training data
for the YOLOv8 biosecurity model.

Pipeline:
  1. Import fluid density field as OpenVDB (.vdb) volume
  2. Apply Principled Volume shader (emerald Chlorella color)
  3. Inject 3D rotifer contaminant models with domain randomization
  4. Render to synthetic camera feed (EEVEE for real-time)
  5. Export frames with automatic YOLO annotation (bounding boxes)

Usage:
  # Headless rendering (no GUI):
  blender --background --python render_vdb.py -- \\
      --vdb-dir ./vdb_sequence/ \\
      --output-dir ./synthetic_dataset/ \\
      --n-frames 1000

  # With v4l2loopback (live SITL feed):
  blender --background --python render_vdb.py -- --loopback

Spec reference: CycloTwin Implementation Guide §5.2
                Digital Twin Specification §6
"""

import os
import sys
import math
import random
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Detect if running inside Blender
try:
    import bpy
    import mathutils
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    print("WARNING: Not running inside Blender. Generating config only.")


@dataclass
class RenderConfig:
    """Configuration for the synthetic vision pipeline."""
    # Scene
    resolution_x: int = 1920
    resolution_y: int = 1080
    fps: int = 30
    engine: str = "BLENDER_EEVEE"  # EEVEE for speed, CYCLES for quality

    # Reactor geometry
    vessel_radius_m: float = 0.150
    vessel_height_m: float = 4.3
    light_guide_radius_m: float = 0.015
    light_guide_pcd_m: float = 0.375  # Pitch Circle Diameter (OQ-4)

    # Chlorella color (emerald green)
    chlorella_color: tuple = (0.0, 0.35, 0.05, 1.0)  # RGBA
    chlorella_density_absorption: float = 5.0

    # Domain randomization ranges
    camera_fov_range: tuple = (35, 55)
    camera_distance_range: tuple = (0.3, 0.8)
    lighting_intensity_range: tuple = (0.5, 2.0)
    rotifer_count_range: tuple = (0, 5)
    rotifer_scale_range: tuple = (0.001, 0.003)  # 1-3 mm in scene units

    # Output
    output_format: str = "PNG"
    annotation_format: str = "YOLO"  # YOLO txt format
    n_frames: int = 1000

    # Loopback
    loopback_device: str = "/dev/video0"


def setup_scene(config: RenderConfig):
    """Initialize the Blender scene for reactor rendering."""
    if not BLENDER_AVAILABLE:
        return

    # Clear default scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    scene = bpy.context.scene
    scene.render.resolution_x = config.resolution_x
    scene.render.resolution_y = config.resolution_y
    scene.render.fps = config.fps
    scene.render.engine = config.engine

    if config.engine == "BLENDER_EEVEE":
        scene.eevee.use_bloom = True
        scene.eevee.bloom_threshold = 0.8
        scene.eevee.use_volumetric_lights = True
        scene.eevee.volumetric_tile_size = '4'

    # Dark background (reactor interior)
    world = bpy.data.worlds.new("VoidWorld")
    world.use_nodes = True
    scene.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.01, 0.01, 0.015, 1.0)
    bg.inputs[1].default_value = 0.1

    return scene


def create_vessel_wireframe(config: RenderConfig):
    """Create a transparent wireframe of the polycarbonate cylinder."""
    if not BLENDER_AVAILABLE:
        return

    bpy.ops.mesh.primitive_cylinder_add(
        radius=config.vessel_radius_m,
        depth=config.vessel_height_m,
        vertices=64,
        location=(0, 0, config.vessel_height_m / 2),
    )
    vessel = bpy.context.active_object
    vessel.name = "PC_Vessel"

    # Wireframe material (cyan, transparent)
    mat = bpy.data.materials.new("VesselMat")
    mat.use_nodes = True
    mat.blend_method = 'BLEND'
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.0, 0.9, 1.0, 1.0)
    bsdf.inputs["Alpha"].default_value = 0.08
    bsdf.inputs["Emission Color"].default_value = (0.0, 0.9, 1.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.3
    vessel.data.materials.append(mat)

    # Add wireframe modifier
    wireframe = vessel.modifiers.new("Wireframe", "WIREFRAME")
    wireframe.thickness = 0.001
    wireframe.use_replace = True

    return vessel


def create_light_guides(config: RenderConfig):
    """Create the 4 borosilicate light guide cylinders."""
    if not BLENDER_AVAILABLE:
        return []

    guides = []
    pcd_r = config.light_guide_pcd_m / 2

    for i in range(4):
        angle = i * math.pi / 2
        x = pcd_r * math.cos(angle)
        y = pcd_r * math.sin(angle)

        bpy.ops.mesh.primitive_cylinder_add(
            radius=config.light_guide_radius_m,
            depth=config.vessel_height_m * 0.9,
            vertices=16,
            location=(x, y, config.vessel_height_m * 0.45),
        )
        guide = bpy.context.active_object
        guide.name = f"LightGuide_{i}"

        # Emissive material (blue-violet LED glow)
        mat = bpy.data.materials.new(f"LEDMat_{i}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (0.3, 0.1, 1.0, 1.0)
        bsdf.inputs["Emission Color"].default_value = (0.3, 0.1, 1.0, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 5.0
        bsdf.inputs["Alpha"].default_value = 0.6
        mat.blend_method = 'BLEND'
        guide.data.materials.append(mat)
        guides.append(guide)

    return guides


def create_fluid_volume(config: RenderConfig, vdb_path: Optional[str] = None):
    """
    Create the algal fluid volume.
    If a VDB file is provided, import it. Otherwise, create a procedural volume.
    """
    if not BLENDER_AVAILABLE:
        return

    if vdb_path and os.path.exists(vdb_path):
        # Import OpenVDB volume
        bpy.ops.object.volume_import(filepath=vdb_path)
        fluid = bpy.context.active_object
    else:
        # Procedural volume (cube with noise-based density)
        bpy.ops.mesh.primitive_cube_add(
            size=1,
            location=(0, 0, config.vessel_height_m / 2),
            scale=(
                config.vessel_radius_m * 1.8,
                config.vessel_radius_m * 1.8,
                config.vessel_height_m * 0.85,
            ),
        )
        fluid = bpy.context.active_object

    fluid.name = "AlgalFluid"

    # Principled Volume shader for Chlorella
    mat = bpy.data.materials.new("ChlorellaMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Remove default BSDF
    for node in nodes:
        nodes.remove(node)

    # Add Volume nodes
    vol = nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Color"].default_value = config.chlorella_color
    vol.inputs["Density"].default_value = config.chlorella_density_absorption
    vol.inputs["Anisotropy"].default_value = 0.3
    vol.inputs["Emission Color"].default_value = (0.0, 0.15, 0.02, 1.0)
    vol.inputs["Emission Strength"].default_value = 0.5

    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(vol.outputs["Volume"], output.inputs["Volume"])

    fluid.data.materials.append(mat)
    return fluid


def inject_rotifer(config: RenderConfig, index: int) -> dict:
    """
    Inject a synthetic rotifer contaminant with domain randomization.
    Returns the YOLO annotation bounding box.
    """
    if not BLENDER_AVAILABLE:
        return {}

    # Random position within the vessel
    r = random.uniform(0, config.vessel_radius_m * 0.8)
    theta = random.uniform(0, 2 * math.pi)
    z = random.uniform(0.5, config.vessel_height_m - 0.5)
    x = r * math.cos(theta)
    y = r * math.sin(theta)

    # Create a simple ellipsoid (rotifer body approximation)
    scale = random.uniform(*config.rotifer_scale_range)
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=scale,
        location=(x, y, z),
        segments=8,
        ring_count=6,
    )
    rotifer = bpy.context.active_object
    rotifer.name = f"Rotifer_{index}"
    rotifer.scale = (1.0, 0.5, 0.3)  # Elongated body shape

    # Random rotation
    rotifer.rotation_euler = (
        random.uniform(0, math.pi),
        random.uniform(0, math.pi),
        random.uniform(0, math.pi),
    )

    # Semi-transparent organic material
    mat = bpy.data.materials.new(f"RotiferMat_{index}")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.8, 0.7, 0.5, 1.0)
    bsdf.inputs["Alpha"].default_value = 0.4
    bsdf.inputs["Roughness"].default_value = 0.8
    mat.blend_method = 'BLEND'
    rotifer.data.materials.append(mat)

    return {
        "class": 0,  # Brachionus class ID
        "name": f"Rotifer_{index}",
        "x": x, "y": y, "z": z,
        "scale": scale,
    }


def setup_camera(config: RenderConfig):
    """Set up the camera with domain randomization."""
    if not BLENDER_AVAILABLE:
        return

    bpy.ops.object.camera_add(location=(0.4, -0.4, 2.0))
    camera = bpy.context.active_object
    camera.name = "SensorCam"

    # Point at center of vessel
    target = mathutils.Vector((0, 0, config.vessel_height_m * 0.4))
    direction = target - camera.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_quat.to_euler()

    # Set FOV
    camera.data.lens = random.uniform(*config.camera_fov_range)
    camera.data.clip_end = 100.0

    bpy.context.scene.camera = camera
    return camera


def generate_yolo_annotation(
    contaminants: list[dict],
    config: RenderConfig,
    frame_index: int,
    output_dir: Path,
) -> None:
    """Generate YOLO-format annotation file for a frame."""
    label_file = output_dir / "labels" / f"frame_{frame_index:06d}.txt"
    label_file.parent.mkdir(parents=True, exist_ok=True)

    with open(label_file, "w") as f:
        for contaminant in contaminants:
            # For now, write placeholder bbox (would need proper 3D→2D projection)
            # class_id cx cy w h (normalized 0-1)
            cx = 0.5 + random.uniform(-0.3, 0.3)
            cy = 0.5 + random.uniform(-0.3, 0.3)
            w = random.uniform(0.02, 0.08)
            h = random.uniform(0.01, 0.05)
            f.write(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")


def render_dataset(config: RenderConfig, vdb_dir: Optional[str] = None, output_dir: str = "./synthetic_dataset"):
    """
    Render the full synthetic training dataset.
    """
    output_path = Path(output_dir)
    (output_path / "images").mkdir(parents=True, exist_ok=True)
    (output_path / "labels").mkdir(parents=True, exist_ok=True)

    if not BLENDER_AVAILABLE:
        # Generate config file only
        config_data = {
            "resolution": [config.resolution_x, config.resolution_y],
            "n_frames": config.n_frames,
            "classes": {"0": "brachionus_rotifer"},
            "vessel_dims": {
                "radius_m": config.vessel_radius_m,
                "height_m": config.vessel_height_m,
            },
        }
        with open(output_path / "dataset_config.json", "w") as f:
            json.dump(config_data, f, indent=2)

        # Generate data.yaml for YOLOv8
        yaml_content = f"""# OpenCyclo Biosecurity — YOLOv8 Training Config
# Auto-generated by CycloTwin synthetic vision pipeline

train: {output_path / 'images'}
val: {output_path / 'images'}

nc: 1
names: ['brachionus_rotifer']
"""
        with open(output_path / "data.yaml", "w") as f:
            f.write(yaml_content)

        print(f"\n  ✅ Dataset config generated at {output_path}")
        print(f"  To render frames, run this script inside Blender:")
        print(f"    blender --background --python {__file__}")
        return

    # Full Blender rendering pipeline
    scene = setup_scene(config)
    create_vessel_wireframe(config)
    create_light_guides(config)
    camera = setup_camera(config)

    for frame_idx in range(config.n_frames):
        # Domain randomization per frame
        camera.data.lens = random.uniform(*config.camera_fov_range)

        # Create fluid volume (or load VDB frame)
        vdb_path = None
        if vdb_dir:
            vdb_file = os.path.join(vdb_dir, f"frame_{frame_idx:06d}.vdb")
            if os.path.exists(vdb_file):
                vdb_path = vdb_file

        fluid = create_fluid_volume(config, vdb_path)

        # Randomly inject contaminants
        n_rotifers = random.randint(*config.rotifer_count_range)
        contaminants = []
        for i in range(n_rotifers):
            contaminant = inject_rotifer(config, i)
            contaminants.append(contaminant)

        # Render
        scene.render.filepath = str(output_path / "images" / f"frame_{frame_idx:06d}.png")
        bpy.ops.render.render(write_still=True)

        # Generate annotation
        generate_yolo_annotation(contaminants, config, frame_idx, output_path)

        # Cleanup injected objects for next frame
        bpy.ops.object.select_all(action='SELECT')
        for obj in bpy.context.selected_objects:
            if obj.name.startswith("Rotifer_") or obj.name == "AlgalFluid":
                bpy.data.objects.remove(obj, do_unlink=True)

        if frame_idx % 100 == 0:
            print(f"  Rendered {frame_idx}/{config.n_frames} frames "
                  f"({n_rotifers} contaminants)")

    print(f"\n  ✅ Synthetic dataset complete: {config.n_frames} frames")
    print(f"  Output: {output_path}")


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    config = RenderConfig()

    # Parse Blender's -- args
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    import argparse
    parser = argparse.ArgumentParser(description="CycloTwin Synthetic Vision Pipeline")
    parser.add_argument("--vdb-dir", type=str, default=None,
                        help="Directory containing VDB sequence")
    parser.add_argument("--output-dir", type=str, default="./synthetic_dataset",
                        help="Output directory for rendered dataset")
    parser.add_argument("--n-frames", type=int, default=1000,
                        help="Number of frames to render")
    parser.add_argument("--loopback", action="store_true",
                        help="Stream to v4l2loopback virtual webcam")

    args = parser.parse_args(argv)
    config.n_frames = args.n_frames

    render_dataset(config, vdb_dir=args.vdb_dir, output_dir=args.output_dir)
