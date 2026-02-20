"""
OpenCyclo V0.1 "Garage Hacker" — Test B: Computer Vision Soft Sensor
======================================================================

Tracks algae growth in the 19L inverted jug by measuring the green
saturation of the culture with a standard USB webcam.

Hardware:
  - Any USB 1080p webcam (e.g., Logitech C270)
  - White paper taped behind the jug as consistent background

Algorithm:
  1. Capture frame every 10 minutes
  2. Mask the background (ROI = jug region)
  3. Convert to HSV color space
  4. Extract mean Green saturation channel
  5. Plot logarithmic growth curve over 5–7 days

Run:
  python vision_growth_tracker.py

  # With a specific camera index:
  python vision_growth_tracker.py --camera 1

  # Faster captures for debugging:
  python vision_growth_tracker.py --interval 30

Spec reference: Garage Hacker Pilot §3 Test B
"""

import time
import csv
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field

try:
    import cv2
    import numpy as np
    CV_AVAILABLE = True
except ImportError:
    CV_AVAILABLE = False
    print("⚠️  OpenCV not found — running in SIMULATION mode")
    print("   Install: pip install opencv-python numpy")


@dataclass
class Config:
    """Vision growth tracker configuration."""
    camera_index: int = 0
    capture_width: int = 1920
    capture_height: int = 1080
    interval_s: float = 600.0     # 10 minutes between captures
    output_dir: str = "growth_data"
    save_frames: bool = True       # Save captured images

    # ROI (Region of Interest) — the jug area in the frame
    # Set to None for full-frame, or (x, y, w, h) for cropped region
    roi: tuple = None  # Will be set during interactive calibration

    # HSV Green detection range for Chlorella
    hsv_green_low: tuple = (25, 20, 20)    # Hue 25-90 captures yellow-green to deep green
    hsv_green_high: tuple = (90, 255, 255)

    # Growth model
    initial_density_estimate: float = 0.1  # g/L (starting culture)


class GrowthTracker:
    """Tracks algae growth via webcam green channel analysis."""

    def __init__(self, config: Config):
        self.config = config
        self.data_points: list[dict] = []
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._cap = None
        self._start_time = time.time()

        if CV_AVAILABLE:
            self._cap = cv2.VideoCapture(config.camera_index)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.capture_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.capture_height)

            if not self._cap.isOpened():
                print(f"  ❌ Cannot open camera {config.camera_index}")
                self._cap = None

    def calibrate_roi(self):
        """Interactive ROI selection — draw a rectangle around the jug."""
        if not CV_AVAILABLE or not self._cap:
            print("  Skipping ROI calibration (no camera)")
            return

        print("\n  📐 ROI Calibration")
        print("  Draw a rectangle around the jug area, then press ENTER")
        print("  Press 'C' to cancel and use full frame\n")

        ret, frame = self._cap.read()
        if not ret:
            print("  ❌ Cannot capture frame for calibration")
            return

        roi = cv2.selectROI("Select Jug Region", frame, fromCenter=False)
        cv2.destroyAllWindows()

        if roi[2] > 0 and roi[3] > 0:
            self.config.roi = roi
            print(f"  ✅ ROI set: x={roi[0]}, y={roi[1]}, w={roi[2]}, h={roi[3]}")

            # Save ROI config
            roi_file = self.output_dir / "roi_config.json"
            with open(roi_file, "w") as f:
                json.dump({"roi": list(roi)}, f)
        else:
            print("  Using full frame (no ROI)")

    def capture_and_analyze(self) -> dict:
        """Capture a frame and extract green saturation metrics."""
        elapsed = time.time() - self._start_time
        timestamp = datetime.now()

        if CV_AVAILABLE and self._cap:
            ret, frame = self._cap.read()
            if not ret:
                return {"error": "capture_failed"}

            # Apply ROI crop
            if self.config.roi:
                x, y, w, h = self.config.roi
                frame = frame[y:y+h, x:x+w]

            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Extract green channel statistics
            h_channel = hsv[:, :, 0]  # Hue
            s_channel = hsv[:, :, 1]  # Saturation
            v_channel = hsv[:, :, 2]  # Value

            # Create green mask
            lower = np.array(self.config.hsv_green_low)
            upper = np.array(self.config.hsv_green_high)
            green_mask = cv2.inRange(hsv, lower, upper)

            # Metrics
            green_ratio = np.count_nonzero(green_mask) / green_mask.size
            mean_saturation = float(np.mean(s_channel))
            mean_green_sat = float(np.mean(s_channel[green_mask > 0])) if np.any(green_mask) else 0.0
            mean_value = float(np.mean(v_channel))

            # Green/Red channel ratio (RGB space) — key density proxy
            b, g, r = cv2.split(frame)
            gr_ratio = float(np.mean(g.astype(float) / (r.astype(float) + 1.0)))

            # Save frame
            if self.config.save_frames:
                frame_path = self.output_dir / f"frame_{len(self.data_points):05d}.jpg"
                cv2.imwrite(str(frame_path), frame)

        else:
            # Simulation: logistic growth curve
            hours = elapsed / 3600
            # Simulated green ratio following logistic growth
            import math
            k = 0.15  # Growth rate
            green_ratio = 0.8 / (1 + math.exp(-k * (hours - 48)))  # Sigmoid over ~4 days
            mean_saturation = 40 + green_ratio * 160
            mean_green_sat = mean_saturation * 1.2
            mean_value = 180 - green_ratio * 100
            gr_ratio = 0.5 + green_ratio * 1.5

        # Build data point
        point = {
            "index": len(self.data_points),
            "timestamp": timestamp.isoformat(),
            "elapsed_hours": round(elapsed / 3600, 2),
            "green_ratio": round(green_ratio, 4),
            "mean_saturation": round(mean_saturation, 1),
            "mean_green_saturation": round(mean_green_sat, 1),
            "mean_brightness": round(mean_value, 1),
            "green_red_ratio": round(gr_ratio, 4),
        }

        self.data_points.append(point)
        return point

    def save_data(self):
        """Save accumulated data to CSV and JSON."""
        if not self.data_points:
            return

        # CSV
        csv_path = self.output_dir / "growth_curve.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.data_points[0].keys())
            writer.writeheader()
            writer.writerows(self.data_points)

        # JSON
        json_path = self.output_dir / "growth_curve.json"
        with open(json_path, "w") as f:
            json.dump(self.data_points, f, indent=2)

        print(f"  💾 Data saved: {csv_path}")

    def print_ascii_chart(self):
        """Print a simple ASCII growth chart."""
        if len(self.data_points) < 2:
            return

        print(f"\n  📈 Growth Curve ({len(self.data_points)} data points)")
        print(f"  {'─'*55}")

        max_green = max(p["green_ratio"] for p in self.data_points)
        chart_width = 40

        for i, point in enumerate(self.data_points):
            bar_len = int((point["green_ratio"] / max(max_green, 0.01)) * chart_width)
            bar = "█" * bar_len
            hours = point["elapsed_hours"]
            print(f"  {hours:6.1f}h │ {bar} {point['green_ratio']:.3f}")

        print(f"  {'─'*55}")

    def cleanup(self):
        """Release camera resources."""
        if self._cap:
            self._cap.release()
        if CV_AVAILABLE:
            cv2.destroyAllWindows()


# ──────────────────────────────────────────────
# Main Loop
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="OpenCyclo V0.1 — Vision Growth Tracker")
    parser.add_argument("--camera", type=int, default=0, help="Camera index")
    parser.add_argument("--interval", type=float, default=600, help="Capture interval (seconds)")
    parser.add_argument("--output", type=str, default="growth_data", help="Output directory")
    parser.add_argument("--no-roi", action="store_true", help="Skip ROI calibration")
    parser.add_argument("--no-save", action="store_true", help="Don't save frame images")
    args = parser.parse_args()

    config = Config(
        camera_index=args.camera,
        interval_s=args.interval,
        output_dir=args.output,
        save_frames=not args.no_save,
    )

    # Load saved ROI if exists
    roi_file = Path(args.output) / "roi_config.json"
    if roi_file.exists():
        with open(roi_file) as f:
            config.roi = tuple(json.load(f)["roi"])
        print(f"  Loaded saved ROI: {config.roi}")

    tracker = GrowthTracker(config)

    # Interactive ROI calibration
    if not args.no_roi and config.roi is None:
        tracker.calibrate_roi()

    print(f"\n  🔬 OpenCyclo V0.1 — Vision Growth Tracker")
    print(f"  Camera: {config.camera_index}")
    print(f"  Interval: {config.interval_s}s ({config.interval_s/60:.0f} min)")
    print(f"  Output: {Path(config.output_dir).absolute()}")
    print(f"  Mode: {'HARDWARE' if CV_AVAILABLE else 'SIMULATION'}")
    print(f"  Press Ctrl+C to stop\n")

    try:
        while True:
            point = tracker.capture_and_analyze()

            if "error" not in point:
                print(f"  [{point['index']:>4}] "
                      f"T={point['elapsed_hours']:>6.1f}h │ "
                      f"Green={point['green_ratio']:.3f} │ "
                      f"Sat={point['mean_saturation']:.0f} │ "
                      f"G/R={point['green_red_ratio']:.3f}")
            else:
                print(f"  ⚠️  Capture failed at {time.time() - tracker._start_time:.0f}s")

            time.sleep(config.interval_s)

    except KeyboardInterrupt:
        print(f"\n\n  ⏹️  Tracking stopped")
        tracker.save_data()
        tracker.print_ascii_chart()
        print()
    finally:
        tracker.cleanup()


if __name__ == "__main__":
    main()
