"""
OpenCyclo V0.1 "Garage Hacker" — Test A: pH-Stat Loop
=======================================================

Validates automated CO₂ dosing on the 19L benchtop prototype.

Hardware:
  - DF-Robot analog pH sensor → ADS1115 ADC → Raspberry Pi I2C
  - 12V CO₂ solenoid valve → 5V relay module → RPi GPIO

Logic:
  - pH > 7.5 → open CO₂ valve (algae consuming too much CO₂, water alkaline)
  - pH < 6.8 → close CO₂ valve (enough dissolved CO₂)
  - Hysteresis band prevents valve chattering

Run:
  python ph_stat_loop.py

Spec reference: Garage Hacker Pilot §3 Test A
"""

import time
import json
import csv
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

# ──────────────────────────────────────────────
# Hardware Abstraction
# ──────────────────────────────────────────────

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("⚠️  Hardware libraries not found — running in SIMULATION mode")


@dataclass
class Config:
    """pH-stat configuration for the Garage V0.1 prototype."""
    # pH control band
    ph_high: float = 7.5      # Open CO₂ when pH exceeds this
    ph_low: float = 6.8       # Close CO₂ when pH drops below this
    ph_setpoint: float = 7.0  # Target (for logging)

    # Hardware pins
    relay_pin: int = 17       # BCM GPIO pin for relay module
    ads_gain: float = 1.0     # ADS1115 gain (±4.096V range)
    ads_channel: int = 0      # ADS1115 analog input channel

    # pH sensor calibration (2-point linear: voltage → pH)
    # Calibrate with pH 4.0 and pH 7.0 buffer solutions
    cal_ph_low: float = 4.0
    cal_v_low: float = 1.50   # Voltage at pH 4.0 (adjust after calibration)
    cal_ph_high: float = 7.0
    cal_v_high: float = 2.50  # Voltage at pH 7.0 (adjust after calibration)

    # Timing
    read_interval_s: float = 2.0   # Sensor reading interval
    log_interval_s: float = 10.0   # CSV logging interval
    display_interval_s: float = 5.0

    # Logging
    log_file: str = "ph_log.csv"


class PHSensor:
    """pH sensor interface via ADS1115 ADC."""

    def __init__(self, config: Config):
        self.config = config
        self._slope = ((config.cal_ph_high - config.cal_ph_low) /
                       (config.cal_v_high - config.cal_v_low))
        self._intercept = config.cal_ph_low - self._slope * config.cal_v_low

        if HARDWARE_AVAILABLE:
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c)
            ads.gain = config.ads_gain
            self._channel = AnalogIn(ads, getattr(ADS, f"P{config.ads_channel}"))
        else:
            self._channel = None
            self._sim_ph = 7.0
            self._sim_valve_open = False

    def read_voltage(self) -> float:
        """Read raw voltage from pH probe."""
        if self._channel:
            return self._channel.voltage
        # Simulation: pH drifts up when valve closed, down when open
        if self._sim_valve_open:
            self._sim_ph -= 0.03  # CO₂ → acidic
        else:
            self._sim_ph += 0.01  # Photosynthesis → alkaline
        self._sim_ph = max(4.0, min(9.0, self._sim_ph))
        # Convert simulated pH back to voltage
        return (self._sim_ph - self._intercept) / self._slope

    def voltage_to_ph(self, voltage: float) -> float:
        """Convert voltage to pH using 2-point calibration."""
        return self._slope * voltage + self._intercept

    def read_ph(self) -> float:
        """Read pH value."""
        v = self.read_voltage()
        return self.voltage_to_ph(v)

    def set_sim_valve(self, state: bool):
        """Set simulated valve state for testing."""
        self._sim_valve_open = state


class CO2Valve:
    """CO₂ solenoid valve controlled via relay."""

    def __init__(self, config: Config):
        self.config = config
        self._is_open = False

        if HARDWARE_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(config.relay_pin, GPIO.OUT, initial=GPIO.LOW)

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open(self):
        """Open CO₂ solenoid (energize relay)."""
        if not self._is_open:
            if HARDWARE_AVAILABLE:
                GPIO.output(self.config.relay_pin, GPIO.HIGH)
            self._is_open = True

    def close(self):
        """Close CO₂ solenoid (de-energize relay)."""
        if self._is_open:
            if HARDWARE_AVAILABLE:
                GPIO.output(self.config.relay_pin, GPIO.LOW)
            self._is_open = False

    def cleanup(self):
        """Release GPIO resources."""
        if HARDWARE_AVAILABLE:
            GPIO.cleanup()


# ──────────────────────────────────────────────
# Main pH-Stat Control Loop
# ──────────────────────────────────────────────

def run_ph_stat(config: Config = None):
    """Run the pH-stat control loop with hysteresis."""
    if config is None:
        config = Config()

    sensor = PHSensor(config)
    valve = CO2Valve(config)
    log_path = Path(config.log_file)

    # Initialize CSV log
    write_header = not log_path.exists()
    log_file = open(log_path, "a", newline="")
    writer = csv.writer(log_file)
    if write_header:
        writer.writerow(["timestamp", "elapsed_s", "ph", "valve_state", "voltage"])

    start_time = time.time()
    last_log = 0
    last_display = 0
    readings = []

    print("\n  🧪 OpenCyclo V0.1 — pH-Stat Control Loop")
    print(f"  Target: pH {config.ph_low} – {config.ph_high}")
    print(f"  Relay: GPIO {config.relay_pin}")
    print(f"  Log: {log_path.absolute()}")
    print(f"  Mode: {'HARDWARE' if HARDWARE_AVAILABLE else 'SIMULATION'}")
    print(f"  Press Ctrl+C to stop\n")
    print(f"  {'Time':>10} │ {'pH':>6} │ {'Valve':>8} │ {'Action'}")
    print(f"  {'─'*10}─┼─{'─'*6}─┼─{'─'*8}─┼─{'─'*20}")

    try:
        while True:
            now = time.time()
            elapsed = now - start_time

            # Read pH
            voltage = sensor.read_voltage()
            ph = sensor.voltage_to_ph(voltage)
            readings.append(ph)

            # pH-stat hysteresis control
            action = ""
            if ph > config.ph_high and not valve.is_open:
                valve.open()
                sensor.set_sim_valve(True)
                action = "🟢 CO₂ OPEN (pH high)"
            elif ph < config.ph_low and valve.is_open:
                valve.close()
                sensor.set_sim_valve(False)
                action = "🔴 CO₂ CLOSED (pH low)"

            # Display
            if now - last_display >= config.display_interval_s or action:
                valve_str = "OPEN" if valve.is_open else "CLOSED"
                elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
                print(f"  {elapsed_str:>10} │ {ph:>6.2f} │ {valve_str:>8} │ {action}")
                last_display = now

            # Log to CSV
            if now - last_log >= config.log_interval_s:
                timestamp = datetime.now().isoformat()
                writer.writerow([timestamp, f"{elapsed:.1f}", f"{ph:.3f}",
                                 "OPEN" if valve.is_open else "CLOSED",
                                 f"{voltage:.4f}"])
                log_file.flush()
                last_log = now

            time.sleep(config.read_interval_s)

    except KeyboardInterrupt:
        print(f"\n\n  ⏹️  Stopped after {elapsed:.0f}s")
        print(f"  Total readings: {len(readings)}")
        if readings:
            print(f"  pH range: {min(readings):.2f} – {max(readings):.2f}")
            print(f"  Mean pH: {sum(readings)/len(readings):.2f}")
        print(f"  Log saved: {log_path.absolute()}\n")
    finally:
        valve.close()
        valve.cleanup()
        log_file.close()


if __name__ == "__main__":
    run_ph_stat()
