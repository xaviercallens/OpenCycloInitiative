"""
OpenCyclo OS — pH-Stat CO₂ Dosing Controller
=============================================

Reads pH from the sensor, runs a PID loop, and controls the CO₂ solenoid
valve to maintain a stable pH setpoint.

Hardware profiles:
  GARAGE:      DF-Robot analog pH sensor via ADS1115 ADC → relay solenoid
  INDUSTRIAL:  Atlas Scientific I2C pH probe → PWM proportional solenoid

Also implements the pH Shock emergency override (SOP-104) for contamination
response: drops pH to 4.5 and holds for 4 hours to kill zooplankton predators
while Chlorella survives.

Spec reference: technical_specifications.md §2.3
Garage reference: OPENCYCLO V0.1-ALPHA §3 Test A
"""

import asyncio
import logging
import time
from typing import Optional

from simple_pid import PID

from config import (
    ACTIVE_PROFILE,
    Profile,
    OperatingState,
    get_config,
)
from utils.logger import log_sensor_data

logger = logging.getLogger("opencyclo")

# ──────────────────────────────────────────────
# Hardware Abstraction Layer
# ──────────────────────────────────────────────

class PHSensorBase:
    """Abstract pH sensor interface."""

    async def read_ph(self) -> float:
        raise NotImplementedError


class GaragePHSensor(PHSensorBase):
    """
    DF-Robot analog pH sensor read via ADS1115 ADC on I2C.

    Calibration:
      - pH 7.0 buffer → record voltage (V_neutral)
      - pH 4.0 buffer → record voltage (V_acid)
      - Linear interpolation: pH = slope * voltage + offset
    """

    def __init__(self):
        self._adc = None
        self._channel = None
        # Default calibration — MUST be calibrated with buffer solutions
        self._slope = -5.7       # mV/pH (typical for DF-Robot V2)
        self._offset = 21.34     # Voltage at pH 0 intercept

    async def initialize(self):
        """Initialize the ADS1115 ADC. Runs in executor to avoid blocking."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_hardware)

    def _init_hardware(self):
        try:
            import board
            import busio
            import adafruit_ads1x15.ads1115 as ADS
            from adafruit_ads1x15.analog_in import AnalogIn

            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c)
            self._channel = AnalogIn(ads, ADS.P0)
            logger.info("Garage pH sensor (ADS1115) initialized on I2C")
        except (ImportError, Exception) as exc:
            logger.warning(f"ADS1115 init failed ({exc}), using simulated pH sensor")
            self._channel = None

    async def read_ph(self) -> float:
        if self._channel is None:
            # Simulated: slowly drift pH upward (algae consuming CO₂)
            return 7.0 + 0.3 * (time.monotonic() % 60) / 60.0

        loop = asyncio.get_running_loop()
        voltage = await loop.run_in_executor(None, lambda: self._channel.voltage)
        ph = self._slope * voltage + self._offset
        return round(max(0.0, min(14.0, ph)), 2)


class IndustrialPHSensor(PHSensorBase):
    """
    Atlas Scientific EZO-pH sensor via I2C (smbus2).

    Default I2C address: 0x63
    Command: 'R' → returns pH as ASCII float
    """

    I2C_ADDRESS = 0x63

    def __init__(self, bus_number: int = 1):
        self._bus_number = bus_number
        self._bus = None

    async def initialize(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_hardware)

    def _init_hardware(self):
        try:
            import smbus2
            self._bus = smbus2.SMBus(self._bus_number)
            logger.info(f"Atlas Scientific pH sensor initialized on I2C bus {self._bus_number}")
        except (ImportError, Exception) as exc:
            logger.warning(f"smbus2 init failed ({exc}), using simulated pH sensor")
            self._bus = None

    async def read_ph(self) -> float:
        if self._bus is None:
            return 6.8 + 0.2 * (time.monotonic() % 30) / 30.0

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._read_atlas)

    def _read_atlas(self) -> float:
        try:
            # Send 'R' (read) command
            self._bus.write_byte(self.I2C_ADDRESS, ord('R'))
            time.sleep(0.9)  # Atlas EZO needs ~900ms for pH reading
            # Read response (max 31 bytes)
            raw = self._bus.read_i2c_block_data(self.I2C_ADDRESS, 0x00, 31)
            if raw[0] == 1:  # Success code
                ph_str = "".join(chr(b) for b in raw[1:] if b != 0)
                return round(float(ph_str), 2)
            return 7.0  # Fallback
        except Exception as exc:
            logger.error(f"Atlas pH read error: {exc}")
            return 7.0


# ──────────────────────────────────────────────
# CO₂ Valve Control
# ──────────────────────────────────────────────

class CO2Valve:
    """Controls the CO₂ solenoid valve via GPIO relay."""

    def __init__(self, relay_pin: int):
        self._pin = relay_pin
        self._gpio = None
        self._is_open = False

    async def initialize(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_gpio)

    def _init_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._pin, GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO
            logger.info(f"CO₂ solenoid valve initialized on GPIO {self._pin}")
        except (ImportError, Exception) as exc:
            logger.warning(f"GPIO init failed ({exc}), using simulated CO₂ valve")
            self._gpio = None

    def open(self):
        """Open the CO₂ valve (energize solenoid)."""
        if not self._is_open:
            if self._gpio:
                self._gpio.output(self._pin, self._gpio.HIGH)
            self._is_open = True
            logger.debug("CO₂ valve OPENED")

    def close(self):
        """Close the CO₂ valve (de-energize solenoid)."""
        if self._is_open:
            if self._gpio:
                self._gpio.output(self._pin, self._gpio.LOW)
            self._is_open = False
            logger.debug("CO₂ valve CLOSED")

    @property
    def is_open(self) -> bool:
        return self._is_open

    def cleanup(self):
        """Release GPIO resources."""
        self.close()
        if self._gpio:
            self._gpio.cleanup(self._pin)


# ──────────────────────────────────────────────
# pH-Stat Controller
# ──────────────────────────────────────────────

class PHStatController:
    """
    Asynchronous pH-stat loop with PID control and pH Shock override.

    In GARAGE mode, operates as a simple relay (on/off) using PID output
    thresholded at 0. In INDUSTRIAL mode, outputs proportional PWM to a
    24V solenoid via the PID output directly.
    """

    def __init__(self):
        cfg = get_config()
        self._ph_cfg = cfg["ph"]
        self._co2_cfg = cfg["co2_valve"]

        # Instantiate hardware
        if ACTIVE_PROFILE == Profile.GARAGE:
            self._sensor = GaragePHSensor()
        else:
            self._sensor = IndustrialPHSensor()

        self._valve = CO2Valve(self._co2_cfg.relay_pin)

        # PID controller
        self._pid = PID(
            Kp=self._ph_cfg.kp,
            Ki=self._ph_cfg.ki,
            Kd=self._ph_cfg.kd,
            setpoint=self._ph_cfg.setpoint,
            output_limits=(0, 100),  # 0-100% valve opening
        )

        # State
        self._running = False
        self._shock_active = False
        self._shock_task: Optional[asyncio.Task] = None
        self._latest_ph: float = 7.0

    async def initialize(self):
        """Initialize sensor and valve hardware."""
        await self._sensor.initialize()
        await self._valve.initialize()
        logger.info(
            f"pH-Stat initialized: setpoint={self._ph_cfg.setpoint}, "
            f"PID=({self._ph_cfg.kp}, {self._ph_cfg.ki}, {self._ph_cfg.kd})"
        )

    @property
    def latest_ph(self) -> float:
        """Most recent pH reading (for main_loop shared state)."""
        return self._latest_ph

    @property
    def valve_is_open(self) -> bool:
        return self._valve.is_open

    async def run(self):
        """
        Main pH-stat control loop. Call this as an asyncio task.

        The loop reads pH at the configured interval, computes PID output,
        and controls the CO₂ solenoid accordingly.
        """
        self._running = True
        logger.info("pH-Stat control loop STARTED")

        try:
            while self._running:
                # Skip PID during pH Shock override
                if self._shock_active:
                    await asyncio.sleep(self._ph_cfg.sample_interval_s)
                    continue

                # Read pH
                ph = await self._sensor.read_ph()
                self._latest_ph = ph
                log_sensor_data(logger, "ph", ph, "pH")

                # PID computation
                # PID error = setpoint - measured
                # Positive output = pH is too high = need more CO₂
                output = self._pid(ph)

                # Garage: simple relay threshold
                if ACTIVE_PROFILE == Profile.GARAGE:
                    if ph > self._ph_cfg.high_threshold:
                        self._valve.open()
                    elif ph < self._ph_cfg.low_threshold:
                        self._valve.close()
                else:
                    # Industrial: proportional control
                    # TODO: PWM duty cycle = output / 100
                    if output > 5.0:  # >5% → open valve
                        self._valve.open()
                    else:
                        self._valve.close()

                await asyncio.sleep(self._ph_cfg.sample_interval_s)

        except asyncio.CancelledError:
            logger.info("pH-Stat control loop cancelled")
        finally:
            self._valve.close()
            self._running = False

    def stop(self):
        """Signal the control loop to stop."""
        self._running = False

    # ── pH Shock Override (SOP-104) ──────────

    async def override_ph_shock(
        self,
        target_ph: Optional[float] = None,
        hold_hours: Optional[float] = None,
    ):
        """
        Emergency contamination response.

        Floods CO₂ to drop pH to target (default 4.5), holds for the specified
        duration, then restores normal PID operation.

        Chlorella's rigid cell wall survives this; soft-bodied zooplankton
        predators undergo osmotic stress and lyse.
        """
        target = target_ph or self._ph_cfg.shock_target
        hours = hold_hours or self._ph_cfg.shock_hold_hours

        logger.warning(
            f"⚠️  pH SHOCK OVERRIDE ACTIVATED: target pH {target}, hold {hours}h"
        )
        self._shock_active = True

        try:
            # Phase 1: Drive pH down by opening CO₂ valve fully
            self._valve.open()
            while True:
                ph = await self._sensor.read_ph()
                self._latest_ph = ph
                log_sensor_data(logger, "ph", ph, "pH", mode="shock_drive")
                if ph <= target:
                    break
                await asyncio.sleep(self._ph_cfg.sample_interval_s)

            # Phase 2: Hold at target pH
            logger.warning(f"pH Shock: reached {target}, holding for {hours} hours")
            hold_seconds = hours * 3600
            start = time.monotonic()
            while (time.monotonic() - start) < hold_seconds:
                ph = await self._sensor.read_ph()
                self._latest_ph = ph
                log_sensor_data(logger, "ph", ph, "pH", mode="shock_hold")

                # Simple bang-bang to maintain target during hold
                if ph > target + 0.2:
                    self._valve.open()
                elif ph < target - 0.2:
                    self._valve.close()

                await asyncio.sleep(self._ph_cfg.sample_interval_s)

            # Phase 3: Restore normal operation
            self._valve.close()
            logger.info("pH Shock: hold complete, restoring normal pH-stat operation")

        except asyncio.CancelledError:
            self._valve.close()
            logger.warning("pH Shock override was cancelled")
        finally:
            self._shock_active = False
            # Reset PID integrator to avoid windup
            self._pid.reset()

    def cleanup(self):
        """Release hardware resources."""
        self.stop()
        self._valve.cleanup()
