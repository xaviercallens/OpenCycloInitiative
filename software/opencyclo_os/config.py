"""
OpenCyclo OS — System Configuration & Constants
================================================

Central configuration file for all hardware pin mappings, sensor addresses,
PID tuning parameters, and system thresholds.

Two profiles are provided:
  - GARAGE (V0.1-Alpha):  19L benchtop prototype with cheap aquarium hardware
  - INDUSTRIAL (V1.0):    1000L SMU with Atlas Scientific probes, VFD, Jetson Nano

Select the active profile by setting ACTIVE_PROFILE below.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ──────────────────────────────────────────────
# System Profile Selection
# ──────────────────────────────────────────────
class Profile(Enum):
    GARAGE = auto()      # V0.1-Alpha: 19L benchtop prototype
    INDUSTRIAL = auto()  # V1.0: 1000L SMU-1000


ACTIVE_PROFILE: Profile = Profile.GARAGE


# ──────────────────────────────────────────────
# Operating States (State Machine)
# ──────────────────────────────────────────────
class OperatingState(Enum):
    IDLE = auto()
    NURSERY = auto()                   # 48h acclimation: continuous 30% LED, low pump
    LOGARITHMIC_GROWTH = auto()        # Ramping LED duty cycle, increasing pump
    STEADY_STATE_TURBIDOSTAT = auto()   # Full turbidostat loop with harvest
    PH_SHOCK = auto()                  # Emergency contamination response (SOP-104)
    SHUTDOWN = auto()


# ──────────────────────────────────────────────
# pH-Stat Configuration
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class PHConfig:
    """pH-stat CO₂ dosing controller parameters."""
    setpoint: float              # Target pH
    high_threshold: float        # pH above this → open CO₂ valve
    low_threshold: float         # pH below this → close CO₂ valve
    shock_target: float          # pH Shock target for contamination (SOP-104)
    shock_hold_hours: float      # Hours to hold pH at shock_target

    # PID gains — MUST be empirically tuned on live culture
    kp: float
    ki: float
    kd: float

    sample_interval_s: float     # Seconds between pH readings


# Garage: simple relay-based on/off with wider deadband
GARAGE_PH = PHConfig(
    setpoint=7.0,
    high_threshold=7.5,
    low_threshold=6.8,
    shock_target=4.5,
    shock_hold_hours=4.0,
    kp=2.0,         # Conservative starting gains for relay control
    ki=0.1,
    kd=0.05,
    sample_interval_s=2.0,
)

# Industrial: Atlas Scientific I2C pH probe, proportional solenoid, tighter control
INDUSTRIAL_PH = PHConfig(
    setpoint=6.8,
    high_threshold=6.9,
    low_threshold=6.7,
    shock_target=4.5,
    shock_hold_hours=4.0,
    kp=5.0,         # Starting gains — MUST be tuned (OQ-3)
    ki=0.5,
    kd=0.1,
    sample_interval_s=1.0,
)


# ──────────────────────────────────────────────
# Vision Sensor Configuration
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class VisionConfig:
    """Computer vision soft sensor parameters."""
    camera_index: int            # OpenCV camera device index
    capture_fps: float           # Frames per second to capture
    resolution: tuple[int, int]  # (width, height)

    # ROI mask — set during calibration (pixel coordinates)
    roi_x: int
    roi_y: int
    roi_w: int
    roi_h: int

    # Biomass density polynomial regression coefficients
    # density_g_L = poly[0]*ratio^2 + poly[1]*ratio + poly[2]
    # ⚠️ MUST be calibrated against physical dry-weight measurements (OQ-3)
    density_poly_coeffs: tuple[float, ...]

    # Biosecurity (industrial only)
    biosecurity_enabled: bool
    biosecurity_model_path: Optional[str]
    biosecurity_confidence_threshold: float
    biosecurity_check_interval: int  # Check every N frames


GARAGE_VISION = VisionConfig(
    camera_index=0,
    capture_fps=0.1,            # 1 frame per 10 seconds is plenty for garage
    resolution=(1280, 720),
    roi_x=200, roi_y=100,       # Calibrate to jug viewport
    roi_w=800, roi_h=500,
    # Placeholder polynomial — MUST be calibrated
    density_poly_coeffs=(0.0, 1.0, 0.0),
    biosecurity_enabled=False,   # No YOLO in garage mode
    biosecurity_model_path=None,
    biosecurity_confidence_threshold=0.85,
    biosecurity_check_interval=100,
)

INDUSTRIAL_VISION = VisionConfig(
    camera_index=0,
    capture_fps=10.0,
    resolution=(1920, 1080),
    roi_x=300, roi_y=200,
    roi_w=1200, roi_h=700,
    density_poly_coeffs=(0.0, 1.0, 0.0),  # Placeholder — calibrate
    biosecurity_enabled=True,
    biosecurity_model_path="models/best_biosecurity.pt",
    biosecurity_confidence_threshold=0.85,
    biosecurity_check_interval=10,        # Check every 10th frame
)


# ──────────────────────────────────────────────
# LED / PWM Configuration
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class LEDConfig:
    """LED PWM and Flashing Light Effect parameters."""
    pwm_pin: int                 # GPIO pin for PWM output (BCM numbering)
    pwm_frequency_hz: float      # Base PWM frequency
    duty_cycle_percent: float    # Duty cycle (50% = Flashing Light Effect)

    # Nursery mode overrides
    nursery_duty_cycle: float    # Continuous ON during nursery (100%)
    nursery_intensity: float     # Brightness during nursery (30%)

    nursery_duration_hours: float  # Hours before transition out of nursery


GARAGE_LED = LEDConfig(
    pwm_pin=18,                  # BCM 18 = hardware PWM on RPi
    pwm_frequency_hz=50.0,       # 50 Hz → 10ms ON, 10ms OFF
    duty_cycle_percent=50.0,
    nursery_duty_cycle=100.0,
    nursery_intensity=30.0,
    nursery_duration_hours=48.0,
)

INDUSTRIAL_LED = LEDConfig(
    pwm_pin=18,
    pwm_frequency_hz=50.0,       # Dynamically adjusted by VFD feedback
    duty_cycle_percent=50.0,
    nursery_duty_cycle=100.0,
    nursery_intensity=30.0,
    nursery_duration_hours=48.0,
)


# ──────────────────────────────────────────────
# Pump / VFD Configuration
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class PumpConfig:
    """Pump and Variable Frequency Drive parameters."""
    # Relay pin (garage) or Modbus address (industrial)
    control_pin: Optional[int]         # GPIO relay pin (garage)
    modbus_address: Optional[int]      # RS-485 Modbus slave address (industrial)
    modbus_port: Optional[str]         # Serial port for RS-485

    nursery_speed_percent: float       # Pump speed during nursery (low shear)
    growth_speed_percent: float        # Pump speed during log growth
    steady_state_speed_percent: float  # Pump speed during turbidostat

    max_flow_rate_lph: float           # Max litres per hour


GARAGE_PUMP = PumpConfig(
    control_pin=17,                    # BCM 17 → relay for 12V DC pump
    modbus_address=None,
    modbus_port=None,
    nursery_speed_percent=30.0,
    growth_speed_percent=60.0,
    steady_state_speed_percent=80.0,
    max_flow_rate_lph=1000.0,          # 12V aquarium pump ~800-1200 L/hr
)

INDUSTRIAL_PUMP = PumpConfig(
    control_pin=None,
    modbus_address=1,
    modbus_port="/dev/ttyUSB0",
    nursery_speed_percent=30.0,
    growth_speed_percent=60.0,
    steady_state_speed_percent=80.0,
    max_flow_rate_lph=5000.0,
)


# ──────────────────────────────────────────────
# CO₂ Solenoid Valve
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class CO2ValveConfig:
    """CO₂ solenoid valve control."""
    relay_pin: int                     # GPIO pin controlling the solenoid relay


GARAGE_CO2 = CO2ValveConfig(relay_pin=27)   # BCM 27
INDUSTRIAL_CO2 = CO2ValveConfig(relay_pin=27)


# ──────────────────────────────────────────────
# Harvest Configuration (Industrial only)
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class HarvestConfig:
    """Turbidostat harvest trigger parameters."""
    density_trigger_g_l: float         # Biomass density threshold for harvest
    harvest_volume_fraction: float     # Fraction of reactor volume to harvest
    harvest_valve_pin: int             # GPIO pin for 3-way motorized ball valve


INDUSTRIAL_HARVEST = HarvestConfig(
    density_trigger_g_l=2.0,           # Placeholder — OQ-7: needs biological data
    harvest_volume_fraction=0.15,      # 15% volume (150L from 1000L)
    harvest_valve_pin=22,
)


# ──────────────────────────────────────────────
# Webhook / Alerts
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class AlertConfig:
    """Webhook and notification settings."""
    enabled: bool
    webhook_url: Optional[str]
    alert_on_biosecurity: bool
    alert_on_ph_shock: bool
    alert_on_state_change: bool


ALERTS = AlertConfig(
    enabled=False,                     # Disabled by default
    webhook_url=None,                  # Set your webhook URL (Slack, Discord, etc.)
    alert_on_biosecurity=True,
    alert_on_ph_shock=True,
    alert_on_state_change=True,
)


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
@dataclass(frozen=True)
class LogConfig:
    """Logging and data recording settings."""
    log_dir: str
    log_level: str
    max_log_size_mb: int
    backup_count: int
    data_log_interval_s: float         # Seconds between sensor data log entries


LOG = LogConfig(
    log_dir="logs",
    log_level="INFO",
    max_log_size_mb=10,
    backup_count=5,
    data_log_interval_s=10.0,
)


# ──────────────────────────────────────────────
# Active Profile Resolution
# ──────────────────────────────────────────────
def get_config():
    """Return the full configuration dict for the active profile."""
    if ACTIVE_PROFILE == Profile.GARAGE:
        return {
            "profile": Profile.GARAGE,
            "ph": GARAGE_PH,
            "vision": GARAGE_VISION,
            "led": GARAGE_LED,
            "pump": GARAGE_PUMP,
            "co2_valve": GARAGE_CO2,
            "harvest": None,           # No automated harvest in garage mode
            "alerts": ALERTS,
            "log": LOG,
        }
    else:
        return {
            "profile": Profile.INDUSTRIAL,
            "ph": INDUSTRIAL_PH,
            "vision": INDUSTRIAL_VISION,
            "led": INDUSTRIAL_LED,
            "pump": INDUSTRIAL_PUMP,
            "co2_valve": INDUSTRIAL_CO2,
            "harvest": INDUSTRIAL_HARVEST,
            "alerts": ALERTS,
            "log": LOG,
        }
