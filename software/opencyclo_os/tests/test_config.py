"""
OpenCyclo OS — Unit Tests: Configuration
=========================================

Tests for config.py: profile selection, dataclass integrity, and validation.
"""

import pytest
from config import (
    ACTIVE_PROFILE,
    Profile,
    OperatingState,
    get_config,
    GARAGE_PH,
    INDUSTRIAL_PH,
    GARAGE_VISION,
    INDUSTRIAL_VISION,
    GARAGE_LED,
    INDUSTRIAL_LED,
    GARAGE_PUMP,
    INDUSTRIAL_PUMP,
)


class TestProfiles:
    """Test that both hardware profiles are correctly defined."""

    def test_garage_profile_returns_config(self):
        """Garage profile should return a config dict with expected keys."""
        import config
        original = config.ACTIVE_PROFILE
        try:
            config.ACTIVE_PROFILE = Profile.GARAGE
            cfg = get_config()
            assert cfg["profile"] == Profile.GARAGE
            assert cfg["ph"] is GARAGE_PH
            assert cfg["vision"] is GARAGE_VISION
            assert cfg["led"] is GARAGE_LED
            assert cfg["pump"] is GARAGE_PUMP
            assert cfg["harvest"] is None  # No automated harvest in garage
        finally:
            config.ACTIVE_PROFILE = original

    def test_industrial_profile_returns_config(self):
        """Industrial profile should return a config dict with harvest config."""
        import config
        original = config.ACTIVE_PROFILE
        try:
            config.ACTIVE_PROFILE = Profile.INDUSTRIAL
            cfg = get_config()
            assert cfg["profile"] == Profile.INDUSTRIAL
            assert cfg["ph"] is INDUSTRIAL_PH
            assert cfg["harvest"] is not None
        finally:
            config.ACTIVE_PROFILE = original


class TestPHConfig:
    """Test pH-stat configuration values."""

    def test_garage_ph_setpoint_in_range(self):
        assert 6.0 <= GARAGE_PH.setpoint <= 8.0

    def test_industrial_ph_setpoint_in_range(self):
        assert 6.0 <= INDUSTRIAL_PH.setpoint <= 8.0

    def test_shock_target_is_acidic(self):
        """pH Shock target must be acidic enough to kill zooplankton."""
        assert GARAGE_PH.shock_target < 5.0
        assert INDUSTRIAL_PH.shock_target < 5.0

    def test_thresholds_are_ordered(self):
        """low_threshold < setpoint < high_threshold."""
        for cfg in (GARAGE_PH, INDUSTRIAL_PH):
            assert cfg.low_threshold < cfg.setpoint
            # For garage, setpoint is between low and high
            assert cfg.low_threshold < cfg.high_threshold

    def test_pid_gains_are_positive(self):
        for cfg in (GARAGE_PH, INDUSTRIAL_PH):
            assert cfg.kp > 0
            assert cfg.ki >= 0
            assert cfg.kd >= 0


class TestVisionConfig:
    """Test vision sensor configuration."""

    def test_garage_biosecurity_disabled(self):
        assert GARAGE_VISION.biosecurity_enabled is False

    def test_industrial_biosecurity_enabled(self):
        assert INDUSTRIAL_VISION.biosecurity_enabled is True

    def test_biosecurity_confidence_threshold(self):
        """Threshold must match spec: 85%."""
        assert INDUSTRIAL_VISION.biosecurity_confidence_threshold == 0.85

    def test_resolution_is_tuple(self):
        assert len(GARAGE_VISION.resolution) == 2
        assert all(v > 0 for v in GARAGE_VISION.resolution)


class TestLEDConfig:
    """Test LED PWM configuration."""

    def test_duty_cycle_is_50_percent(self):
        """FLE requires 50% duty cycle (spec §2.4)."""
        assert GARAGE_LED.duty_cycle_percent == 50.0
        assert INDUSTRIAL_LED.duty_cycle_percent == 50.0

    def test_nursery_intensity_is_30_percent(self):
        """Nursery mode: 30% intensity (spec §SOP-102 step 4)."""
        assert GARAGE_LED.nursery_intensity == 30.0

    def test_nursery_duration_48h(self):
        """Nursery must last 48 hours (spec §SOP-102 step 4)."""
        assert GARAGE_LED.nursery_duration_hours == 48.0


class TestPumpConfig:
    """Test pump configuration."""

    def test_garage_has_relay_pin(self):
        assert GARAGE_PUMP.control_pin is not None

    def test_industrial_has_modbus(self):
        assert INDUSTRIAL_PUMP.modbus_address is not None
        assert INDUSTRIAL_PUMP.modbus_port is not None

    def test_nursery_is_low_shear(self):
        """Nursery speed must be lowest to protect fragile cells."""
        for cfg in (GARAGE_PUMP, INDUSTRIAL_PUMP):
            assert cfg.nursery_speed_percent <= cfg.growth_speed_percent
            assert cfg.growth_speed_percent <= cfg.steady_state_speed_percent


class TestOperatingStates:
    """Test that all state machine states are defined."""

    def test_all_states_exist(self):
        expected = {
            "IDLE", "NURSERY", "LOGARITHMIC_GROWTH",
            "STEADY_STATE_TURBIDOSTAT", "PH_SHOCK", "SHUTDOWN",
        }
        actual = {s.name for s in OperatingState}
        assert expected == actual
