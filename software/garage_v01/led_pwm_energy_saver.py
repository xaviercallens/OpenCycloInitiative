"""
OpenCyclo V0.1 "Garage Hacker" — Test C: PWM Light Pulsing
=============================================================

Cuts LED power consumption by 50% without reducing algae growth
by exploiting the Flashing Light Effect (FLE).

Hardware:
  - 12V LED grow light strip (Red/Blue 4:1)
  - N-channel logic-level MOSFET (e.g., IRLZ44N)
  - Arduino/RPi PWM pin → MOSFET gate
  - 12V PSU → MOSFET drain → LED strip

Principle:
  At 50 Hz PWM (10ms ON, 10ms OFF), human eyes see continuous light
  but the LEDs are OFF 50% of the time, halving electricity cost.
  The algae cells' photosynthetic antenna (PSU) recovers during the
  dark phase (Han model x2→x1 transition), so net growth is identical
  to continuous illumination.

Run:
  python led_pwm_energy_saver.py

  # Custom frequency and duty cycle:
  python led_pwm_energy_saver.py --freq 82.5 --duty 50

  # Sweep test (find optimal frequency):
  python led_pwm_energy_saver.py --sweep

Spec reference: Garage Hacker Pilot §3 Test C
"""

import time
import argparse
from dataclasses import dataclass

try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("⚠️  RPi.GPIO not found — running in SIMULATION mode")


@dataclass
class Config:
    """LED PWM configuration."""
    pwm_pin: int = 18            # BCM GPIO 18 (hardware PWM capable on RPi)
    frequency_hz: float = 50.0   # PWM frequency
    duty_cycle_pct: float = 50.0 # Duty cycle (50% = half power)


class LEDController:
    """Controls LED grow lights via hardware PWM."""

    def __init__(self, config: Config):
        self.config = config
        self._pwm = None
        self._running = False

        if HARDWARE_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(config.pwm_pin, GPIO.OUT)
            self._pwm = GPIO.PWM(config.pwm_pin, config.frequency_hz)

    def start(self, frequency_hz: float = None, duty_pct: float = None):
        """Start PWM output."""
        freq = frequency_hz or self.config.frequency_hz
        duty = duty_pct or self.config.duty_cycle_pct

        if self._pwm:
            self._pwm.ChangeFrequency(freq)
            self._pwm.start(duty)
        self._running = True

        period_ms = 1000.0 / freq
        on_ms = period_ms * duty / 100.0
        off_ms = period_ms - on_ms

        return {
            "frequency_hz": freq,
            "duty_cycle_pct": duty,
            "period_ms": round(period_ms, 2),
            "on_time_ms": round(on_ms, 2),
            "off_time_ms": round(off_ms, 2),
            "power_savings_pct": round(100 - duty, 1),
        }

    def set_frequency(self, freq_hz: float):
        """Change PWM frequency while running."""
        self.config.frequency_hz = freq_hz
        if self._pwm:
            self._pwm.ChangeFrequency(freq_hz)

    def set_duty(self, duty_pct: float):
        """Change duty cycle while running."""
        self.config.duty_cycle_pct = duty_pct
        if self._pwm:
            self._pwm.ChangeDutyCycle(duty_pct)

    def stop(self):
        """Stop PWM (LEDs off)."""
        if self._pwm:
            self._pwm.stop()
        self._running = False

    def continuous(self):
        """Switch to continuous mode (100% duty — no energy saving)."""
        return self.start(duty_pct=100.0)

    def cleanup(self):
        """Release GPIO resources."""
        self.stop()
        if HARDWARE_AVAILABLE:
            GPIO.cleanup()


def run_constant_mode(config: Config):
    """Run LEDs at fixed PWM settings."""
    controller = LEDController(config)

    print(f"\n  💡 OpenCyclo V0.1 — LED PWM Energy Saver")
    print(f"  Mode: CONSTANT")
    print(f"  GPIO: BCM {config.pwm_pin}")
    print(f"  Hardware: {'YES' if HARDWARE_AVAILABLE else 'SIMULATION'}")

    info = controller.start()
    print(f"\n  Frequency:    {info['frequency_hz']:.1f} Hz")
    print(f"  Duty Cycle:   {info['duty_cycle_pct']:.1f}%")
    print(f"  Period:       {info['period_ms']:.2f} ms")
    print(f"  ON time:      {info['on_time_ms']:.2f} ms")
    print(f"  OFF time:     {info['off_time_ms']:.2f} ms")
    print(f"  Power Saved:  {info['power_savings_pct']:.1f}%  ⚡")
    print(f"\n  To your eyes: LEDs appear solid.")
    print(f"  To your electricity meter: you just cut power by {info['power_savings_pct']:.0f}%!")
    print(f"\n  Press Ctrl+C to stop\n")

    try:
        while True:
            if not HARDWARE_AVAILABLE:
                cycle = (time.time() * config.frequency_hz) % 1.0
                state = "ON " if cycle < (config.duty_cycle_pct / 100.0) else "OFF"
                print(f"  [SIM] LED: {state}  ({config.frequency_hz:.0f} Hz, {config.duty_cycle_pct:.0f}%)", end="\r")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\n  ⏹️  LEDs stopped")
    finally:
        controller.cleanup()


def run_sweep_test(config: Config):
    """Sweep through frequencies to help find the optimal FLE frequency."""
    controller = LEDController(config)

    frequencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 120, 150, 200]

    print(f"\n  💡 OpenCyclo V0.1 — LED PWM Frequency Sweep")
    print(f"  Duty Cycle: {config.duty_cycle_pct}%")
    print(f"  Testing {len(frequencies)} frequencies")
    print(f"  Each frequency runs for 5 seconds")
    print(f"  Watch the culture response over several days!")
    print(f"\n  {'Freq (Hz)':>10} │ {'Period (ms)':>12} │ {'ON (ms)':>10} │ {'OFF (ms)':>10} │ {'Savings':>8}")
    print(f"  {'─'*10}─┼─{'─'*12}─┼─{'─'*10}─┼─{'─'*10}─┼─{'─'*8}")

    try:
        for freq in frequencies:
            info = controller.start(frequency_hz=freq)
            print(f"  {freq:>10.0f} │ {info['period_ms']:>12.2f} │ "
                  f"{info['on_time_ms']:>10.2f} │ {info['off_time_ms']:>10.2f} │ "
                  f"{info['power_savings_pct']:>7.1f}%")
            time.sleep(5)

        print(f"\n  ✅ Sweep complete!")
        print(f"  Recommended: 50–100 Hz at 50% duty for optimal FLE")
        print(f"  (See Han model analysis: physics/cyclo_twin/han_model.py)\n")

    except KeyboardInterrupt:
        print("\n\n  ⏹️  Sweep stopped")
    finally:
        controller.cleanup()


def main():
    parser = argparse.ArgumentParser(description="OpenCyclo V0.1 — LED PWM Energy Saver")
    parser.add_argument("--freq", type=float, default=50.0, help="PWM frequency in Hz")
    parser.add_argument("--duty", type=float, default=50.0, help="Duty cycle percentage")
    parser.add_argument("--pin", type=int, default=18, help="BCM GPIO pin")
    parser.add_argument("--sweep", action="store_true", help="Run frequency sweep test")
    args = parser.parse_args()

    config = Config(
        pwm_pin=args.pin,
        frequency_hz=args.freq,
        duty_cycle_pct=args.duty,
    )

    if args.sweep:
        run_sweep_test(config)
    else:
        run_constant_mode(config)


if __name__ == "__main__":
    main()
