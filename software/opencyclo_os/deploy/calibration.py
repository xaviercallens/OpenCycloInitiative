"""
OpenCyclo OS — Guided Calibration Script
=========================================

Interactive script to calibrate the vision-based biomass density sensor.

Procedure:
  1. Capture ROI (Region of Interest) from the camera preview
  2. Collect paired samples: (Green/Red ratio) ↔ (Dry Weight g/L)
  3. Fit a polynomial regression curve to the data
  4. Save calibration file to disk for use by vision_density.py

Usage:
  python calibration.py              # Interactive mode
  python calibration.py --roi-only   # Set ROI mask only
  python calibration.py --fit-only   # Fit polynomial from saved CSV

Spec reference: technical_specifications.md §2.4 (Vision Soft Sensor)
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import get_config

CALIBRATION_DIR = Path(__file__).resolve().parent.parent / "calibration_data"
ROI_FILE = CALIBRATION_DIR / "roi_mask.json"
SAMPLES_FILE = CALIBRATION_DIR / "density_samples.csv"
COEFFS_FILE = CALIBRATION_DIR / "density_poly_coeffs.json"


def ensure_dirs():
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)


def capture_roi():
    """Interactive ROI selection using OpenCV."""
    try:
        import cv2
    except ImportError:
        print("ERROR: OpenCV not installed. Run: pip install opencv-python")
        return

    cfg = get_config()
    vcfg = cfg["vision"]
    cam = cv2.VideoCapture(vcfg.camera_index)

    if not cam.isOpened():
        print("ERROR: Cannot open camera. Check camera_index in config.py")
        return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, vcfg.resolution[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, vcfg.resolution[1])

    print("\n╔══════════════════════════════════════════╗")
    print("║   ROI (Region of Interest) Selection     ║")
    print("╠══════════════════════════════════════════╣")
    print("║  1. A camera preview window will open    ║")
    print("║  2. Draw a rectangle around the fluid    ║")
    print("║     viewing area (avoid bubbles/edges)   ║")
    print("║  3. Press ENTER to confirm               ║")
    print("║  4. Press 'c' to cancel and retry        ║")
    print("╚══════════════════════════════════════════╝\n")

    ret, frame = cam.read()
    if not ret:
        print("ERROR: Failed to capture frame")
        cam.release()
        return

    roi = cv2.selectROI("Select ROI — Press ENTER to confirm", frame, showCrosshair=True)
    cv2.destroyAllWindows()
    cam.release()

    if roi[2] == 0 or roi[3] == 0:
        print("No ROI selected. Aborting.")
        return

    roi_data = {
        "x": int(roi[0]),
        "y": int(roi[1]),
        "width": int(roi[2]),
        "height": int(roi[3]),
        "timestamp": datetime.now().isoformat(),
        "resolution": list(vcfg.resolution),
    }

    ensure_dirs()
    with open(ROI_FILE, "w") as f:
        json.dump(roi_data, f, indent=2)

    print(f"\n✅ ROI saved to {ROI_FILE}")
    print(f"   Region: x={roi_data['x']}, y={roi_data['y']}, "
          f"w={roi_data['width']}, h={roi_data['height']}")


def collect_sample():
    """Capture a single paired data point: Green/Red ratio ↔ Dry Weight."""
    try:
        import cv2
    except ImportError:
        print("ERROR: OpenCV not installed.")
        return

    cfg = get_config()
    vcfg = cfg["vision"]

    # Load ROI
    if not ROI_FILE.exists():
        print("ERROR: ROI mask not set. Run: python calibration.py --roi-only")
        return

    with open(ROI_FILE) as f:
        roi_data = json.load(f)

    cam = cv2.VideoCapture(vcfg.camera_index)
    if not cam.isOpened():
        print("ERROR: Cannot open camera.")
        return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, vcfg.resolution[0])
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, vcfg.resolution[1])

    # Average multiple frames for stability
    print("\n📸 Capturing 10 frames for averaging...")
    ratios = []
    for i in range(10):
        ret, frame = cam.read()
        if not ret:
            continue
        x, y, w, h = roi_data["x"], roi_data["y"], roi_data["width"], roi_data["height"]
        roi = frame[y:y+h, x:x+w]

        mean_bgr = cv2.mean(roi)[:3]
        blue, green, red = mean_bgr
        if red < 1.0:
            red = 1.0
        ratio = green / red
        ratios.append(ratio)
        time.sleep(0.1)

    cam.release()

    if not ratios:
        print("ERROR: No frames captured.")
        return

    avg_ratio = np.mean(ratios)
    std_ratio = np.std(ratios)

    print(f"\n   Green/Red ratio: {avg_ratio:.4f} ± {std_ratio:.4f}")
    print(f"   (Based on {len(ratios)} frames)")

    # Get physical measurement from user
    print("\n" + "─" * 40)
    print("Now measure the Dry Weight of the culture:")
    print("  1. Take a 50mL sample from the reactor")
    print("  2. Centrifuge at 4000 RPM for 10 min")
    print("  3. Decant, dry pellet at 105°C for 24h")
    print("  4. Weigh the dried pellet")
    print("─" * 40)

    try:
        dry_weight = float(input("\nEnter Dry Weight (g/L): ").strip())
    except (ValueError, KeyboardInterrupt):
        print("Invalid input. Aborting.")
        return

    # Append to CSV
    ensure_dirs()
    file_exists = SAMPLES_FILE.exists()
    with open(SAMPLES_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "timestamp", "green_red_ratio", "ratio_std", "dry_weight_g_l", "n_frames"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now().isoformat(),
            "green_red_ratio": f"{avg_ratio:.6f}",
            "ratio_std": f"{std_ratio:.6f}",
            "dry_weight_g_l": f"{dry_weight:.4f}",
            "n_frames": len(ratios),
        })

    print(f"\n✅ Sample recorded: ratio={avg_ratio:.4f} → density={dry_weight:.4f} g/L")
    print(f"   Saved to {SAMPLES_FILE}")

    # Show current sample count
    with open(SAMPLES_FILE) as f:
        count = sum(1 for _ in csv.DictReader(f))
    print(f"   Total calibration samples: {count}")
    if count < 5:
        print(f"   ⚠️  Need at least 5 samples for a reliable polynomial fit (have {count})")


def fit_polynomial():
    """Fit a polynomial regression to the calibration data."""
    if not SAMPLES_FILE.exists():
        print("ERROR: No calibration data found. Collect samples first.")
        return

    with open(SAMPLES_FILE) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if len(rows) < 3:
        print(f"ERROR: Need at least 3 data points (have {len(rows)})")
        return

    ratios = np.array([float(r["green_red_ratio"]) for r in rows])
    densities = np.array([float(r["dry_weight_g_l"]) for r in rows])

    # Fit polynomials of degree 1 through 3, select best by R²
    best_degree = 1
    best_r2 = -1.0
    best_coeffs = None

    for degree in range(1, min(4, len(rows))):
        coeffs = np.polyfit(ratios, densities, degree)
        predicted = np.polyval(coeffs, ratios)
        ss_res = np.sum((densities - predicted) ** 2)
        ss_tot = np.sum((densities - np.mean(densities)) ** 2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        print(f"   Degree {degree}: R² = {r2:.6f}, coeffs = {coeffs.tolist()}")

        if r2 > best_r2:
            best_r2 = r2
            best_degree = degree
            best_coeffs = coeffs

    print(f"\n   ✅ Selected: degree {best_degree} polynomial (R² = {best_r2:.6f})")

    # Save coefficients
    ensure_dirs()
    calib_data = {
        "degree": best_degree,
        "coefficients": best_coeffs.tolist(),
        "r_squared": best_r2,
        "n_samples": len(rows),
        "ratio_range": [float(ratios.min()), float(ratios.max())],
        "density_range": [float(densities.min()), float(densities.max())],
        "timestamp": datetime.now().isoformat(),
    }

    with open(COEFFS_FILE, "w") as f:
        json.dump(calib_data, f, indent=2)

    print(f"   Coefficients saved to {COEFFS_FILE}")
    print(f"\n   To use these coefficients, update config.py:")
    print(f"     density_poly_coeffs = {tuple(best_coeffs.tolist())}")


def main():
    parser = argparse.ArgumentParser(
        prog="opencyclo-calibration",
        description="OpenCyclo Vision Sensor Calibration Tool",
    )
    parser.add_argument("--roi-only", action="store_true",
                        help="Set ROI mask only")
    parser.add_argument("--sample", action="store_true",
                        help="Collect a single calibration sample")
    parser.add_argument("--fit-only", action="store_true",
                        help="Fit polynomial from saved CSV data")
    args = parser.parse_args()

    print("\n  🌿 OpenCyclo — Vision Sensor Calibration\n")

    if args.roi_only:
        capture_roi()
    elif args.sample:
        collect_sample()
    elif args.fit_only:
        fit_polynomial()
    else:
        # Full guided flow
        print("This tool calibrates the vision-based biomass density sensor.")
        print("The process requires physical lab measurements.\n")
        print("Steps:")
        print("  1. Set the camera ROI (region of interest)")
        print("  2. Collect 5+ paired samples (camera ratio ↔ dry weight)")
        print("  3. Fit a polynomial regression curve\n")

        choice = input("Start with ROI setup? (y/n): ").strip().lower()
        if choice == "y":
            capture_roi()

        print("\nTo collect a sample, run:")
        print("  python calibration.py --sample")
        print("\nTo fit the curve after collecting 5+ samples:")
        print("  python calibration.py --fit-only")


if __name__ == "__main__":
    main()
