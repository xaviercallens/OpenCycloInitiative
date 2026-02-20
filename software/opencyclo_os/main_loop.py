"""
OpenCyclo OS — Core Orchestrator
=================================

The central daemon that manages the bioreactor state machine,
coordinates all subsystem controllers, and handles lifecycle events.

State Machine:
  IDLE → NURSERY → LOGARITHMIC_GROWTH → STEADY_STATE_TURBIDOSTAT
                                          ↕
                                       PH_SHOCK (emergency)
                                          ↓
                                       SHUTDOWN

Subsystems managed:
  1. ph_stat_co2   — pH-stat CO₂ dosing PID controller
  2. vision_density — Computer vision biomass soft sensor
  3. led_pwm_sync   — LED Flashing Light Effect controller
  4. Pump relay     — Vortex pump on/off (garage) or VFD Modbus (industrial)

Usage:
  python main_loop.py              # Run with active profile from config.py
  python main_loop.py --simulate   # Force simulation mode (no hardware)

Spec reference: technical_specifications.md §2.1
Garage reference: OPENCYCLO V0.1-ALPHA §3
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from typing import Optional

from config import (
    ACTIVE_PROFILE,
    Profile,
    OperatingState,
    get_config,
)
from ph_stat_co2 import PHStatController
from vision_density import VisionDensitySensor
from led_pwm_sync import LEDController
from utils.logger import setup_logger, log_sensor_data
from utils.webhook import send_webhook

logger: Optional[logging.Logger] = None


# ──────────────────────────────────────────────
# Pump Controller (simple relay for garage)
# ──────────────────────────────────────────────

class PumpController:
    """
    Vortex pump controller.

    GARAGE:      12V DC pump controlled via GPIO relay (on/off + simple speed)
    INDUSTRIAL:  VFD controlled via RS-485 Modbus (continuous speed control)
    """

    def __init__(self):
        cfg = get_config()
        self._pump_cfg = cfg["pump"]
        self._gpio = None
        self._modbus_client = None
        self._current_speed_pct: float = 0.0
        self._actual_frequency_hz: float = 0.0

    async def initialize(self):
        loop = asyncio.get_running_loop()
        if ACTIVE_PROFILE == Profile.GARAGE:
            await loop.run_in_executor(None, self._init_relay)
        else:
            await loop.run_in_executor(None, self._init_modbus)

    def _init_relay(self):
        pin = self._pump_cfg.control_pin
        if pin is None:
            logger.info("Pump: no relay pin configured, using simulation")
            return
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
            self._gpio = GPIO
            logger.info(f"Pump relay initialized on GPIO {pin}")
        except (ImportError, Exception) as exc:
            logger.warning(f"Pump GPIO init failed ({exc}), using simulation")

    def _init_modbus(self):
        addr = self._pump_cfg.modbus_address
        port = self._pump_cfg.modbus_port
        if addr is None or port is None:
            logger.info("Pump: no Modbus config, using simulation")
            return
        try:
            from pymodbus.client import ModbusSerialClient
            self._modbus_client = ModbusSerialClient(
                port=port, baudrate=9600, parity="N", stopbits=1, timeout=1,
            )
            self._modbus_client.connect()
            logger.info(f"Pump VFD Modbus connected on {port} (addr={addr})")
        except (ImportError, Exception) as exc:
            logger.warning(f"Modbus init failed ({exc}), using simulation")

    def set_speed(self, percent: float):
        """Set pump speed as a percentage of maximum (0-100)."""
        percent = max(0.0, min(100.0, percent))
        self._current_speed_pct = percent

        if ACTIVE_PROFILE == Profile.GARAGE:
            # Garage: relay ON/OFF (no speed control on DC pump without PWM)
            if self._gpio and self._pump_cfg.control_pin:
                if percent > 0:
                    self._gpio.output(self._pump_cfg.control_pin, self._gpio.HIGH)
                else:
                    self._gpio.output(self._pump_cfg.control_pin, self._gpio.LOW)
            # Simulate a base frequency for LED sync
            self._actual_frequency_hz = 50.0 * (percent / 100.0) if percent > 0 else 0.0
        else:
            # Industrial: write speed to VFD via Modbus
            if self._modbus_client:
                try:
                    # Typical VFD register: 0x2000 = frequency reference (0-10000 = 0.0-100.0 Hz)
                    freq_value = int(percent * 100)  # 0-10000
                    self._modbus_client.write_register(
                        0x2000, freq_value,
                        slave=self._pump_cfg.modbus_address,
                    )
                    # Read actual frequency back
                    result = self._modbus_client.read_holding_registers(
                        0x2001, 1, slave=self._pump_cfg.modbus_address,
                    )
                    if not result.isError():
                        self._actual_frequency_hz = result.registers[0] / 100.0
                except Exception as exc:
                    logger.error(f"Modbus write failed: {exc}")
            else:
                self._actual_frequency_hz = 50.0 * (percent / 100.0)

        log_sensor_data(
            logger, "pump_speed", percent, "%",
            actual_freq_hz=self._actual_frequency_hz,
        )

    @property
    def speed_percent(self) -> float:
        return self._current_speed_pct

    @property
    def actual_frequency_hz(self) -> float:
        return self._actual_frequency_hz

    def stop(self):
        self.set_speed(0)

    def cleanup(self):
        self.stop()
        if self._gpio and self._pump_cfg.control_pin:
            self._gpio.cleanup(self._pump_cfg.control_pin)
        if self._modbus_client:
            self._modbus_client.close()


# ──────────────────────────────────────────────
# Main Orchestrator
# ──────────────────────────────────────────────

class OpenCycloOrchestrator:
    """
    Central control daemon managing the bioreactor state machine
    and coordinating all subsystem controllers.
    """

    def __init__(self):
        cfg = get_config()
        self._cfg = cfg
        self._state = OperatingState.IDLE
        self._prev_state: Optional[OperatingState] = None

        # Subsystem controllers
        self._ph_stat = PHStatController()
        self._vision = VisionDensitySensor()
        self._led = LEDController()
        self._pump = PumpController()

        # Task handles
        self._tasks: list[asyncio.Task] = []

        # Nursery timer
        self._nursery_start: Optional[float] = None

        # Harvest config (industrial only)
        self._harvest_cfg = cfg.get("harvest")
        self._is_harvesting = False

    async def initialize(self):
        """Initialize all subsystem hardware."""
        logger.info("=" * 60)
        logger.info("  OpenCyclo OS — Initializing")
        logger.info(f"  Profile: {ACTIVE_PROFILE.name}")
        logger.info("=" * 60)

        await self._pump.initialize()
        await self._ph_stat.initialize()
        await self._vision.initialize()
        await self._led.initialize()

        logger.info("All subsystems initialized successfully")

    async def run(self):
        """
        Main orchestration loop.

        Starts all subsystem tasks, manages state transitions, and
        runs until shutdown is requested.
        """
        # Start subsystem tasks
        self._tasks = [
            asyncio.create_task(self._ph_stat.run(), name="ph_stat"),
            asyncio.create_task(self._vision.run(), name="vision"),
            asyncio.create_task(self._led.run(), name="led"),
        ]

        # Transition to NURSERY mode on startup
        await self._transition_to(OperatingState.NURSERY)

        try:
            while self._state != OperatingState.SHUTDOWN:
                await self._state_machine_tick()
                await asyncio.sleep(2.0)  # State machine poll interval
        except asyncio.CancelledError:
            logger.info("Orchestrator cancelled")
        finally:
            await self.shutdown()

    async def _state_machine_tick(self):
        """Evaluate state transition conditions on each tick."""

        if self._state == OperatingState.NURSERY:
            # Check if nursery period is complete
            if self._nursery_start is not None:
                elapsed_h = (time.monotonic() - self._nursery_start) / 3600.0
                nursery_duration = self._cfg["led"].nursery_duration_hours

                if elapsed_h >= nursery_duration:
                    logger.info(
                        f"Nursery period complete ({nursery_duration}h elapsed). "
                        "Transitioning to LOGARITHMIC_GROWTH."
                    )
                    await self._transition_to(OperatingState.LOGARITHMIC_GROWTH)

        elif self._state == OperatingState.LOGARITHMIC_GROWTH:
            # Check if biomass density has reached the turbidostat trigger
            density = self._vision.latest_density
            if self._harvest_cfg and density >= self._harvest_cfg.density_trigger_g_l:
                logger.info(
                    f"Biomass density {density:.2f} g/L ≥ trigger "
                    f"{self._harvest_cfg.density_trigger_g_l} g/L. "
                    "Transitioning to STEADY_STATE_TURBIDOSTAT."
                )
                await self._transition_to(OperatingState.STEADY_STATE_TURBIDOSTAT)

        elif self._state == OperatingState.STEADY_STATE_TURBIDOSTAT:
            # Monitor density and trigger harvests
            density = self._vision.latest_density
            if self._harvest_cfg and density >= self._harvest_cfg.density_trigger_g_l and not self._is_harvesting:
                asyncio.create_task(self._trigger_harvest())

            # In garage mode, just log (no automated harvest)
            if ACTIVE_PROFILE == Profile.GARAGE:
                pass  # Operator manually harvests via siphon

        # Sync LED PWM with pump frequency (all states)
        self._led.update_pump_frequency(self._pump.actual_frequency_hz)

    async def _transition_to(self, new_state: OperatingState):
        """Execute a state transition with all side effects."""
        old = self._state
        self._state = new_state
        self._prev_state = old

        logger.info(f"STATE TRANSITION: {old.name} → {new_state.name}")

        # Apply state-specific settings
        if new_state == OperatingState.NURSERY:
            self._nursery_start = time.monotonic()
            self._pump.set_speed(self._cfg["pump"].nursery_speed_percent)
            self._led.set_state(OperatingState.NURSERY)

        elif new_state == OperatingState.LOGARITHMIC_GROWTH:
            self._pump.set_speed(self._cfg["pump"].growth_speed_percent)
            self._led.set_state(OperatingState.LOGARITHMIC_GROWTH)

        elif new_state == OperatingState.STEADY_STATE_TURBIDOSTAT:
            self._pump.set_speed(self._cfg["pump"].steady_state_speed_percent)
            self._led.set_state(OperatingState.STEADY_STATE_TURBIDOSTAT)

        elif new_state == OperatingState.PH_SHOCK:
            # Keep pump running to maintain vortex mixing
            self._led.set_state(OperatingState.PH_SHOCK)
            # pH shock is driven by ph_stat_co2.override_ph_shock()

        elif new_state == OperatingState.SHUTDOWN:
            self._pump.stop()
            self._led.set_state(OperatingState.SHUTDOWN)

        # Fire webhook
        alerts = self._cfg["alerts"]
        if alerts.enabled and alerts.alert_on_state_change:
            await send_webhook(
                url=alerts.webhook_url,
                event="state_change",
                message=f"Bioreactor state: {old.name} → {new_state.name}",
                severity="info",
                data={"old_state": old.name, "new_state": new_state.name},
            )

    async def _trigger_harvest(self):
        """
        Trigger the turbidostat harvest cycle.

        INDUSTRIAL: Opens the 3-way motorized ball valve to divert
        culture through the hydrocyclone at 3 Bar.

        GARAGE: Logs a notification for manual siphon harvest.
        """
        if ACTIVE_PROFILE == Profile.GARAGE:
            density = self._vision.latest_density
            logger.info(
                f"🌿 HARVEST READY: Biomass density = {density:.2f} g/L. "
                "Turn off pump, let settle in neck for 12h, siphon the paste."
            )
            return

        # Industrial: automated valve operation
        logger.info("Triggering turbidostat harvest cycle...")
        self._is_harvesting = True
        try:
            harvest_cfg = self._cfg.get("harvest")
            if not harvest_cfg or not harvest_cfg.harvest_valve_pin:
                logger.warning("Harvest valve not configured, skipping...")
                return
                
            pin = harvest_cfg.harvest_valve_pin
            try:
                import RPi.GPIO as GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                
                # 1. Open 3-way valve
                logger.info(f"Opening harvest valve on GPIO {pin}")
                GPIO.output(pin, GPIO.HIGH)
                
                # 2. Divert 15% volume through hydrocyclone at 3 Bar
                volume_l = 1000.0 * harvest_cfg.harvest_volume_fraction
                speed_pct = self._pump.speed_percent
                if speed_pct <= 0:
                    logger.error("Pump is stopped, cannot harvest!")
                    GPIO.output(pin, GPIO.LOW)
                    return
                    
                flow_rate_lph = self._cfg["pump"].max_flow_rate_lph * (speed_pct / 100.0)
                duration_s = (volume_l / flow_rate_lph) * 3600.0
                logger.info(f"Harvesting {volume_l:.1f}L @ {flow_rate_lph:.1f} L/hr... waiting {duration_s:.1f}s")
                
                # 3. Wait for harvest volume to pass
                await asyncio.sleep(duration_s)
                
                # 4. Close valve
                logger.info(f"Closing harvest valve on GPIO {pin}")
                GPIO.output(pin, GPIO.LOW)
                
                # 5. Draw fresh media to restore reactor volume
                logger.info("Harvest complete. Drawing fresh media (gravity top-up).")
                
            except ImportError:
                logger.warning("RPi.GPIO not found (simulation mode) — Harvest simulated.")
                await asyncio.sleep(5.0)
                logger.info("Simulated harvest complete.")
                
        finally:
            self._is_harvesting = False

    async def trigger_ph_shock(self):
        """
        Manually trigger a pH Shock contamination response (SOP-104).

        Can be called from an API endpoint or CLI command.
        """
        logger.warning("⚠️  Manual pH Shock triggered by operator")
        await self._transition_to(OperatingState.PH_SHOCK)

        await self._ph_stat.override_ph_shock()

        # Restore previous operating state after shock completes
        restore_state = self._prev_state or OperatingState.LOGARITHMIC_GROWTH
        logger.info(f"pH Shock complete. Restoring state: {restore_state.name}")
        await self._transition_to(restore_state)

    async def shutdown(self):
        """Gracefully shut down all subsystems."""
        logger.info("Initiating graceful shutdown...")
        await self._transition_to(OperatingState.SHUTDOWN)

        # Cancel all subsystem tasks
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Cleanup hardware
        self._ph_stat.cleanup()
        self._vision.cleanup()
        self._led.cleanup()
        self._pump.cleanup()

        logger.info("OpenCyclo OS shutdown complete.")


# ──────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────

async def main():
    """Main async entry point."""
    global logger
    cfg = get_config()
    logger = setup_logger(
        log_dir=cfg["log"].log_dir,
        log_level=cfg["log"].log_level,
        max_bytes=cfg["log"].max_log_size_mb * 1024 * 1024,
        backup_count=cfg["log"].backup_count,
    )

    orchestrator = OpenCycloOrchestrator()

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for all signals
            signal.signal(sig, lambda s, f: _signal_handler())

    try:
        await orchestrator.initialize()

        # Run orchestrator with shutdown watcher
        orchestrator_task = asyncio.create_task(orchestrator.run())

        # Wait for shutdown signal
        await shutdown_event.wait()
        orchestrator_task.cancel()
        try:
            await orchestrator_task
        except asyncio.CancelledError:
            pass

    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.exception(f"Fatal error: {exc}")
    finally:
        await orchestrator.shutdown()


def cli():
    """CLI entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        prog="opencyclo-os",
        description="OpenCyclo OS — Bioreactor Control Daemon",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Force simulation mode (no hardware I/O)",
    )
    parser.add_argument(
        "--profile",
        choices=["garage", "industrial"],
        default=None,
        help="Override the active hardware profile",
    )
    args = parser.parse_args()

    # Profile override
    if args.profile:
        import config
        config.ACTIVE_PROFILE = Profile[args.profile.upper()]
        print(f"Profile override: {config.ACTIVE_PROFILE.name}")

    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║    🌿 OpenCyclo OS v0.1-alpha        ║")
    print("  ║    Cyclo-Vortex Bioreactor Control    ║")
    print("  ╚══════════════════════════════════════╝")
    print()

    asyncio.run(main())


if __name__ == "__main__":
    cli()
