"""
OpenCyclo OS — Computer Vision Soft Sensor
==========================================

Non-invasive biomass density estimation via webcam image analysis.
Replaces expensive inline turbidity probes with a camera + math.

Algorithm:
  1. Capture frame from webcam looking at reactor viewport
  2. Mask to Region of Interest (ROI)
  3. Convert to HSV color space
  4. Compute Green channel saturation ratio
  5. Map ratio to Dry Weight (g/L) via calibrated polynomial regression

Optionally (INDUSTRIAL profile only):
  6. Run YOLOv8 INT8 inference for biosecurity (rotifer/biofilm detection)
  7. Trigger webhook alert if confidence ≥ 85%

Spec reference: technical_specifications.md §2.2
Garage reference: OPENCYCLO V0.1-ALPHA §3 Test B
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from config import (
    ACTIVE_PROFILE,
    Profile,
    get_config,
)
from utils.logger import log_sensor_data
from utils.webhook import send_webhook

logger = logging.getLogger("opencyclo")


class VisionDensitySensor:
    """
    Asynchronous computer vision soft sensor for biomass density estimation.

    Captures frames from a webcam, analyzes color in HSV space, and maps
    Green/Red ratio to biomass concentration via a polynomial regression curve.
    """

    def __init__(self):
        cfg = get_config()
        self._vcfg = cfg["vision"]
        self._alerts = cfg["alerts"]

        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._latest_density: float = 0.0
        self._latest_green_ratio: float = 0.0
        self._frame_count: int = 0

        # Biosecurity (industrial only)
        self._yolo_model = None

        # Snapshot directory for growth curve logging
        self._snapshot_dir = Path("data/snapshots")

    async def initialize(self):
        """Initialize camera and optional YOLO model."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_camera)

        if self._vcfg.biosecurity_enabled and self._vcfg.biosecurity_model_path:
            await loop.run_in_executor(None, self._init_yolo)

    def _init_camera(self):
        """Open the webcam via OpenCV."""
        try:
            self._cap = cv2.VideoCapture(self._vcfg.camera_index)
            if not self._cap.isOpened():
                logger.warning("Camera failed to open, using simulated vision sensor")
                self._cap = None
                return

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._vcfg.resolution[0])
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._vcfg.resolution[1])

            actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.info(f"Camera initialized: {actual_w}x{actual_h} on device {self._vcfg.camera_index}")

        except Exception as exc:
            logger.warning(f"Camera init failed ({exc}), using simulated vision sensor")
            self._cap = None

    def _init_yolo(self):
        """Load YOLOv8 model for biosecurity detection (industrial only)."""
        try:
            from ultralytics import YOLO
            model_path = self._vcfg.biosecurity_model_path
            self._yolo_model = YOLO(model_path, task="detect")
            logger.info(f"YOLOv8 biosecurity model loaded from {model_path}")
        except (ImportError, Exception) as exc:
            logger.warning(f"YOLOv8 model load failed ({exc}), biosecurity detection disabled")
            self._yolo_model = None

    @property
    def latest_density(self) -> float:
        """Most recent biomass density estimate (g/L)."""
        return self._latest_density

    @property
    def latest_green_ratio(self) -> float:
        """Most recent Green/Red channel ratio (raw)."""
        return self._latest_green_ratio

    def _extract_roi(self, frame: np.ndarray) -> np.ndarray:
        """Crop frame to the configured Region of Interest."""
        x, y = self._vcfg.roi_x, self._vcfg.roi_y
        w, h = self._vcfg.roi_w, self._vcfg.roi_h
        # Clamp to frame bounds
        fh, fw = frame.shape[:2]
        x = min(x, fw - 1)
        y = min(y, fh - 1)
        w = min(w, fw - x)
        h = min(h, fh - y)
        return frame[y:y+h, x:x+w]

    def _compute_green_ratio(self, roi: np.ndarray) -> float:
        """
        Compute the Green/Red channel ratio in HSV space.

        As algae density increases, the culture transitions from clear →
        pale green → vivid green → dark emerald → opaque. The Green
        saturation channel and Green/Red ratio track this progression.
        """
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Extract mean Hue and Saturation
        mean_hsv = cv2.mean(hsv)[:3]    # (H, S, V)

        # Also compute in RGB space for the Green/Red ratio
        mean_bgr = cv2.mean(roi)[:3]    # (B, G, R)
        blue, green, red = mean_bgr

        # Avoid division by zero
        if red < 1.0:
            red = 1.0

        green_red_ratio = green / red
        return green_red_ratio

    def _ratio_to_density(self, ratio: float) -> float:
        """
        Map Green/Red ratio to biomass dry weight (g/L) using polynomial regression.

        The polynomial coefficients MUST be calibrated empirically:
          1. Grow culture from inoculation through exponential phase
          2. At regular intervals, record webcam Green/Red ratio
          3. Simultaneously sample 50mL, centrifuge, dry, weigh → dry weight (g/L)
          4. Fit polynomial: density = c[0]*ratio^N + ... + c[-1]

        ⚠️ Default coefficients are PLACEHOLDER — calibration is required (OQ-3).
        """
        coeffs = self._vcfg.density_poly_coeffs
        density = sum(c * (ratio ** (len(coeffs) - 1 - i)) for i, c in enumerate(coeffs))
        return max(0.0, density)

    async def _capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame from the camera (or simulate)."""
        if self._cap is None:
            # Simulate increasing green density over time
            return self._simulate_frame()

        loop = asyncio.get_running_loop()
        ret, frame = await loop.run_in_executor(None, self._cap.read)
        if not ret or frame is None:
            logger.warning("Frame capture failed")
            return None
        return frame

    def _simulate_frame(self) -> np.ndarray:
        """
        Generate a simulated frame for testing without a camera.

        Simulates a culture that gets progressively greener over time.
        """
        elapsed_minutes = (time.monotonic() % 600) / 600.0  # Cycle every 10 min
        # Interpolate from pale (low density) to vivid green (high density)
        green_intensity = int(80 + 175 * elapsed_minutes)
        red_intensity = int(200 - 150 * elapsed_minutes)
        blue_intensity = int(180 - 100 * elapsed_minutes)

        frame = np.full(
            (self._vcfg.resolution[1], self._vcfg.resolution[0], 3),
            (blue_intensity, green_intensity, red_intensity),
            dtype=np.uint8,
        )
        return frame

    def _save_snapshot(self, frame: np.ndarray, density: float, ratio: float):
        """Save a timestamped snapshot for growth curve construction."""
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{ts}_d{density:.3f}_r{ratio:.3f}.jpg"
        filepath = self._snapshot_dir / filename
        cv2.imwrite(str(filepath), frame)

    async def _run_biosecurity(self, frame: np.ndarray):
        """
        Run YOLOv8 inference to detect zooplankton predators or biofilm.

        Only runs in INDUSTRIAL profile when model is loaded.
        Triggers webhook if any detection confidence ≥ threshold.
        """
        if self._yolo_model is None:
            return

        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(None, lambda: self._yolo_model(frame, verbose=False))

        for result in results:
            for box in result.boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_name = result.names.get(cls_id, f"class_{cls_id}")

                if conf >= self._vcfg.biosecurity_confidence_threshold:
                    logger.warning(
                        f"🚨 BIOSECURITY ALERT: {cls_name} detected "
                        f"(confidence: {conf:.1%})"
                    )
                    await send_webhook(
                        url=self._alerts.webhook_url if self._alerts.enabled else None,
                        event="biosecurity_alert",
                        message=f"Detected {cls_name} with {conf:.1%} confidence",
                        severity="critical",
                        data={"class": cls_name, "confidence": conf},
                    )

    async def run(self):
        """
        Main vision sensor loop. Call as an asyncio task.

        Captures frames at the configured interval, computes biomass density,
        logs data, and optionally runs biosecurity inference.
        """
        self._running = True
        interval = 1.0 / self._vcfg.capture_fps if self._vcfg.capture_fps > 0 else 10.0
        logger.info(f"Vision sensor started: {self._vcfg.capture_fps} FPS, interval={interval:.1f}s")

        try:
            while self._running:
                frame = await self._capture_frame()
                if frame is None:
                    await asyncio.sleep(interval)
                    continue

                self._frame_count += 1

                # Extract ROI and compute density
                roi = self._extract_roi(frame)
                ratio = self._compute_green_ratio(roi)
                density = self._ratio_to_density(ratio)

                self._latest_green_ratio = ratio
                self._latest_density = density

                log_sensor_data(
                    logger, "biomass_density", density, "g/L",
                    green_red_ratio=ratio,
                    frame=self._frame_count,
                )

                # Save periodic snapshots (every 100 frames)
                if self._frame_count % 100 == 0:
                    self._save_snapshot(frame, density, ratio)

                # Biosecurity check (every N frames)
                if (
                    self._vcfg.biosecurity_enabled
                    and self._frame_count % self._vcfg.biosecurity_check_interval == 0
                ):
                    await self._run_biosecurity(frame)

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            logger.info("Vision sensor loop cancelled")
        finally:
            self._running = False

    def stop(self):
        """Signal the sensor loop to stop."""
        self._running = False

    def cleanup(self):
        """Release camera resources."""
        self.stop()
        if self._cap is not None:
            self._cap.release()
            logger.info("Camera released")
