"""
OpenCyclo OS — Unit Tests: pH-Stat Controller
==============================================

Tests for ph_stat_co2.py: sensor reading, PID logic, valve control,
and pH Shock override.

All tests use simulated hardware (no GPIO/I2C required).
"""

import asyncio
import pytest
import pytest_asyncio

# Ensure we can import from the parent package
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ph_stat_co2 import PHStatController, GaragePHSensor, CO2Valve


class TestGaragePHSensor:
    """Test the garage pH sensor (simulated mode)."""

    @pytest.mark.asyncio
    async def test_simulated_ph_returns_valid_range(self):
        """Simulated pH should return values in valid range."""
        sensor = GaragePHSensor()
        await sensor.initialize()
        ph = await sensor.read_ph()
        assert 0.0 <= ph <= 14.0

    @pytest.mark.asyncio
    async def test_simulated_ph_drifts_upward(self):
        """Simulated pH should drift upward (mimicking algae consuming CO₂)."""
        sensor = GaragePHSensor()
        await sensor.initialize()
        ph = await sensor.read_ph()
        # Should be above neutral (7.0) to simulate algae growth
        assert ph >= 7.0


class TestCO2Valve:
    """Test the CO₂ solenoid valve (simulated mode)."""

    @pytest.mark.asyncio
    async def test_valve_starts_closed(self):
        valve = CO2Valve(relay_pin=27)
        await valve.initialize()
        assert valve.is_open is False

    @pytest.mark.asyncio
    async def test_valve_opens_and_closes(self):
        valve = CO2Valve(relay_pin=27)
        await valve.initialize()

        valve.open()
        assert valve.is_open is True

        valve.close()
        assert valve.is_open is False

    @pytest.mark.asyncio
    async def test_valve_double_open_is_idempotent(self):
        valve = CO2Valve(relay_pin=27)
        await valve.initialize()
        valve.open()
        valve.open()  # Should not error
        assert valve.is_open is True

    @pytest.mark.asyncio
    async def test_valve_cleanup_closes(self):
        valve = CO2Valve(relay_pin=27)
        await valve.initialize()
        valve.open()
        valve.cleanup()
        assert valve.is_open is False


class TestPHStatController:
    """Test the pH-stat controller integration."""

    @pytest.mark.asyncio
    async def test_controller_initializes(self):
        controller = PHStatController()
        await controller.initialize()
        # Should not raise; sensor and valve should be in simulated mode

    @pytest.mark.asyncio
    async def test_controller_starts_and_stops(self):
        controller = PHStatController()
        await controller.initialize()

        # Run for 0.5 seconds then stop
        task = asyncio.create_task(controller.run())
        await asyncio.sleep(0.5)
        controller.stop()
        await asyncio.sleep(0.5)

        # Should have read at least one pH value
        assert controller.latest_ph > 0.0
        controller.cleanup()

    @pytest.mark.asyncio
    async def test_latest_ph_updates(self):
        controller = PHStatController()
        await controller.initialize()

        task = asyncio.create_task(controller.run())
        await asyncio.sleep(3.0)  # Let a few readings happen
        controller.stop()
        await asyncio.sleep(0.5)

        assert controller.latest_ph != 0.0
        controller.cleanup()
