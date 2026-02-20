"""
OpenCyclo OS — LED PWM Sync Controller
=======================================

Manages the LED grow light arrays to exploit the biological Flashing Light
Effect (FLE), where rapid light/dark cycling at the Plastoquinone turnover
rate maximizes photon use efficiency while cutting electrical costs by 50%.

Hardware profiles:
  GARAGE:      LED strip via MOSFET on Arduino PWM pin (simple fixed 50Hz)
  INDUSTRIAL:  LED arrays synced to VFD pump speed (dynamic PWM frequency)

In NURSERY mode, LEDs run at continuous 30% intensity (no pulsing) for
48 hours to allow photo-acclimation of freshly inoculated cells.

The Flashing Light Effect (FLE):
  - Chlorophyll absorbs a photon → electron enters Photosystem II
  - Plastoquinone (PQ) pool accepts the electron → ~10ms to recycle
  - During PQ turnover, additional photons are wasted as heat/fluorescence
  - By pulsing light at 50% duty cycle matched to PQ turnover, every photon
    is productively absorbed → same growth, half the electricity

Spec reference: technical_specifications.md §2.4
Garage reference: OPENCYCLO V0.1-ALPHA §3 Test C
"""

import asyncio
import logging
from typing import Optional

from config import (
    ACTIVE_PROFILE,
    Profile,
    OperatingState,
    get_config,
)
from utils.logger import log_sensor_data

logger = logging.getLogger("opencyclo")


class LEDController:
    """
    Asynchronous LED PWM controller with Flashing Light Effect.

    Controls LED brightness and pulsing via hardware PWM on the
    Raspberry Pi (or simulated on desktop).
    """

    def __init__(self):
        cfg = get_config()
        self._led_cfg = cfg["led"]
        self._gpio = None
        self._pwm = None
        self._running = False
        self._current_state: OperatingState = OperatingState.IDLE
        self._current_frequency: float = self._led_cfg.pwm_frequency_hz
        self._current_duty_cycle: float = 0.0

        # Shared state: pump frequency (Hz) — updated by main_loop
        self._pump_frequency_hz: float = 0.0

    async def initialize(self):
        """Initialize GPIO PWM hardware."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_hardware)

    def _init_hardware(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._led_cfg.pwm_pin, GPIO.OUT)

            # Start PWM at 0% duty cycle (LEDs off)
            self._pwm = GPIO.PWM(self._led_cfg.pwm_pin, self._led_cfg.pwm_frequency_hz)
            self._pwm.start(0)
            self._gpio = GPIO

            logger.info(
                f"LED PWM initialized on GPIO {self._led_cfg.pwm_pin} "
                f"at {self._led_cfg.pwm_frequency_hz} Hz"
            )
        except (ImportError, Exception) as exc:
            logger.warning(f"GPIO PWM init failed ({exc}), using simulated LED controller")
            self._gpio = None
            self._pwm = None

    def set_state(self, state: OperatingState):
        """
        Update the LED behavior based on the current operating state.

        Args:
            state: The new operating state from the state machine.
        """
        self._current_state = state

        if state == OperatingState.NURSERY:
            # Nursery: continuous (no pulsing), 30% intensity for photo-acclimation
            self._set_pwm(
                frequency=1000.0,  # High frequency = appears continuous
                duty_cycle=self._led_cfg.nursery_intensity,
            )
            logger.info("LED mode: NURSERY (continuous 30%)")

        elif state in (OperatingState.LOGARITHMIC_GROWTH, OperatingState.STEADY_STATE_TURBIDOSTAT):
            # Growth modes: Flashing Light Effect at 50% duty cycle
            self._set_pwm(
                frequency=self._current_frequency,
                duty_cycle=self._led_cfg.duty_cycle_percent,
            )
            logger.info(
                f"LED mode: FLE ({self._current_frequency:.1f} Hz, "
                f"{self._led_cfg.duty_cycle_percent:.0f}% duty)"
            )

        elif state == OperatingState.PH_SHOCK:
            # During pH shock, maintain current LED state (algae still photosynthesizing)
            pass

        elif state in (OperatingState.IDLE, OperatingState.SHUTDOWN):
            # LEDs off
            self._set_pwm(frequency=self._current_frequency, duty_cycle=0.0)
            logger.info("LED mode: OFF")

    def update_pump_frequency(self, pump_freq_hz: float):
        """
        Update the LED PWM frequency based on VFD pump speed.

        In the INDUSTRIAL profile, the LED pulse timing must match the
        interval at which cells traverse the illuminated borosilicate
        light guides inside the vortex. Faster vortex = faster PWM.

        The relationship between pump frequency and optimal PWM frequency
        depends on reactor geometry and must be derived from CFD simulation
        (see OQ-4 in COMPONENT_MATRIX.md).

        For now, a simple linear scaling is used as a placeholder:
          PWM_freq = base_freq * (pump_freq / base_pump_freq)
        """
        self._pump_frequency_hz = pump_freq_hz

        if ACTIVE_PROFILE == Profile.GARAGE:
            # Garage: fixed PWM frequency, no VFD sync
            return

        if pump_freq_hz <= 0:
            return

        # Placeholder linear scaling — replace with CFD-derived formula
        base_pump_freq = 50.0  # Hz (full speed reference)
        scaling_factor = pump_freq_hz / base_pump_freq
        new_freq = self._led_cfg.pwm_frequency_hz * max(0.5, min(2.0, scaling_factor))

        if abs(new_freq - self._current_frequency) > 0.5:  # Hysteresis
            self._current_frequency = new_freq
            if self._current_state in (
                OperatingState.LOGARITHMIC_GROWTH,
                OperatingState.STEADY_STATE_TURBIDOSTAT,
            ):
                self._set_pwm(new_freq, self._led_cfg.duty_cycle_percent)
                log_sensor_data(
                    logger, "led_pwm_freq", new_freq, "Hz",
                    pump_freq=pump_freq_hz,
                )

    def _set_pwm(self, frequency: float, duty_cycle: float):
        """Apply PWM settings to hardware (or log in simulation mode)."""
        self._current_duty_cycle = duty_cycle

        if self._pwm is not None:
            try:
                self._pwm.ChangeFrequency(max(1.0, frequency))
                self._pwm.ChangeDutyCycle(max(0.0, min(100.0, duty_cycle)))
            except Exception as exc:
                logger.error(f"PWM update failed: {exc}")
        else:
            logger.debug(f"LED (sim): freq={frequency:.1f}Hz, duty={duty_cycle:.1f}%")

    @property
    def current_frequency(self) -> float:
        return self._current_frequency

    @property
    def current_duty_cycle(self) -> float:
        return self._current_duty_cycle

    async def run(self):
        """
        Main LED controller loop.

        Mostly passive — state changes come via set_state() and
        update_pump_frequency() calls from main_loop. This loop
        handles periodic logging and nursery-to-growth transitions.
        """
        self._running = True
        logger.info("LED controller started")

        nursery_elapsed_s = 0.0
        poll_interval = 5.0  # Check every 5 seconds

        try:
            while self._running:
                # Track nursery duration
                if self._current_state == OperatingState.NURSERY:
                    nursery_elapsed_s += poll_interval
                    hours = nursery_elapsed_s / 3600.0
                    if hours >= self._led_cfg.nursery_duration_hours:
                        logger.info(
                            f"Nursery period complete ({self._led_cfg.nursery_duration_hours}h). "
                            "Ready for transition to LOGARITHMIC_GROWTH."
                        )
                        # Don't auto-transition — main_loop decides

                # Periodic status log
                log_sensor_data(
                    logger, "led_status", self._current_duty_cycle, "%",
                    frequency=self._current_frequency,
                    state=self._current_state.name,
                )

                await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            logger.info("LED controller cancelled")
        finally:
            self._set_pwm(self._current_frequency, 0.0)  # LEDs off
            self._running = False

    def stop(self):
        """Signal the controller to stop."""
        self._running = False

    def cleanup(self):
        """Release GPIO resources."""
        self.stop()
        if self._pwm is not None:
            self._pwm.stop()
        if self._gpio is not None:
            self._gpio.cleanup(self._led_cfg.pwm_pin)
