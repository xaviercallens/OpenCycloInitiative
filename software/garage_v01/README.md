# 🛠️ OpenCyclo V0.1 — "Garage Hacker" Prototype Scripts

**Benchtop 19-Liter Proof-of-Concept Software**

Three standalone Python scripts that validate the core physics and AI logic of the OpenCyclo system on a €150/$150 hardware setup.

---

## 📦 Hardware Requirements

| Component | Purpose | Est. Cost |
|---|---|---|
| 19L clear PET water jug (inverted) | Reactor vessel | €5 |
| 12V DC brushless aquarium pump | Cyclonic vortex | €15 |
| Limewood (basswood) airstone | CO₂ microbubble sparger | €5 |
| CO₂ source (SodaStream or yeast bottle) | Carbon feed | €10-30 |
| 12V CO₂ solenoid valve | Automated dosing | €15 |
| 5m Red/Blue LED grow strip (12V) | Photosynthesis | €10 |
| Raspberry Pi (any model) | Compute node | €35-65 |
| ADS1115 ADC module | Analog pH reading | €5 |
| DF-Robot pH sensor kit | pH measurement | €15 |
| USB webcam (1080p) | Vision soft sensor | €15 |
| N-channel MOSFET (IRLZ44N) | LED PWM switching | €2 |
| **TOTAL** | | **~€130-180** |

---

## 🧪 Test A — pH-Stat Loop (`ph_stat_loop.py`)

Automated CO₂ dosing via pH feedback control.

```bash
# Real hardware:
python ph_stat_loop.py

# Simulation mode (no hardware needed):
python ph_stat_loop.py
# → Runs automatically in simulation if RPi.GPIO not detected
```

**What it proves:** Zero-waste direct carbon absorption — CO₂ is dosed precisely when the algae consume it.

---

## 🔬 Test B — Vision Growth Tracker (`vision_growth_tracker.py`)

Webcam-based biomass density estimation using green saturation analysis.

```bash
# With USB webcam:
python vision_growth_tracker.py --camera 0 --interval 600

# Quick test (30s interval):
python vision_growth_tracker.py --interval 30

# Simulation mode:
python vision_growth_tracker.py --interval 5  # Fast sim
```

**What it proves:** Non-invasive, real-time growth monitoring — no lab equipment needed.

---

## 💡 Test C — LED PWM Energy Saver (`led_pwm_energy_saver.py`)

50% power reduction via Flashing Light Effect (FLE) exploitation.

```bash
# Run at 50 Hz, 50% duty:
python led_pwm_energy_saver.py --freq 50 --duty 50

# Frequency sweep (test different rates):
python led_pwm_energy_saver.py --sweep
```

**What it proves:** The Flashing Light Effect is real — algae grow identically at 50% power.

---

## 📊 Results

After 7-10 days of operation:

1. **pH log** → `ph_log.csv` — continuous record of automated CO₂ control
2. **Growth curve** → `growth_data/growth_curve.csv` — logarithmic biomass increase
3. **Energy data** → Compare electricity meter readings with and without PWM

**The harvest:** Turn off the pump. Algae settle into the neck over 12 hours. Siphon the green paste, dry in the sun, weigh the flakes. **Multiply dry weight × 1.83 = CO₂ permanently removed from the atmosphere.**

---

## 🔗 Next Steps

Once your 19L garage vortex is humming, you've mastered the fundamentals. You're ready to:

1. Scale to the full [1000L OpenCyclo system](../../docs/technical_specifications.md)
2. Use your garage algae as the **seed culture** for the industrial reactor
3. Connect to [Cyclo-Earth](../../physics/cyclo_earth/) to track your CO₂ impact globally
