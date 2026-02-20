"""
OpenCyclo OS — Unit Tests: Vision Density Sensor
=================================================

Tests for vision_density.py: frame capture, HSV analysis, density mapping.
Uses simulated camera (no physical hardware required).
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vision_density import VisionDensitySensor


class TestVisionDensitySensor:
    """Test the vision soft sensor in simulated mode."""

    @pytest.mark.asyncio
    async def test_sensor_initializes(self):
        sensor = VisionDensitySensor()
        await sensor.initialize()
        # Should not raise; camera should fall through to simulation mode

    @pytest.mark.asyncio
    async def test_simulated_frame_is_valid(self):
        sensor = VisionDensitySensor()
        await sensor.initialize()
        frame = sensor._simulate_frame()
        assert frame is not None
        assert frame.shape[2] == 3  # BGR channels
        assert frame.shape[0] > 0
        assert frame.shape[1] > 0

    @pytest.mark.asyncio
    async def test_green_ratio_is_positive(self):
        sensor = VisionDensitySensor()
        await sensor.initialize()
        frame = sensor._simulate_frame()
        roi = sensor._extract_roi(frame)
        ratio = sensor._compute_green_ratio(roi)
        assert ratio > 0.0

    @pytest.mark.asyncio
    async def test_density_is_non_negative(self):
        sensor = VisionDensitySensor()
        await sensor.initialize()
        density = sensor._ratio_to_density(1.5)
        assert density >= 0.0

    @pytest.mark.asyncio
    async def test_sensor_runs_and_updates_density(self):
        sensor = VisionDensitySensor()
        await sensor.initialize()

        task = asyncio.create_task(sensor.run())
        await asyncio.sleep(2.0)
        sensor.stop()
        await asyncio.sleep(0.5)

        # Density should have been updated at least once
        assert sensor.latest_density >= 0.0
        assert sensor.latest_green_ratio > 0.0
        sensor.cleanup()

    def test_polynomial_mapping(self):
        """Test that the polynomial correctly maps input values."""
        sensor = VisionDensitySensor()
        # Default placeholder poly: 0*x^2 + 1*x + 0 → identity
        assert sensor._ratio_to_density(0.0) == 0.0
        assert sensor._ratio_to_density(1.0) == pytest.approx(1.0)
        assert sensor._ratio_to_density(2.5) == pytest.approx(2.5)
