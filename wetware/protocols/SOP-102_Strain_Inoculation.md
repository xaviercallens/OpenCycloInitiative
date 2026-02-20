# SOP-102: Strain Inoculation & Nursery Mode Activation

> **OpenCyclo Initiative** | Standard Operating Procedure  
> **Version:** 0.1-alpha  
> **License:** OpenMTA  
> **Organism:** *Chlorella vulgaris* (UTEX 2714)

---

## 1. Scope

This procedure covers:
1. Sourcing and receiving the *Chlorella vulgaris* stock culture
2. Propagating a seed inoculum in a 2L flask → 50L carboy scale-up
3. Inoculating the main bioreactor vessel
4. Activating the AI Nursery Mode (48h acclimation period)

---

## 2. Strain Sourcing

### 2.1 Recommended Source

| Attribute | Value |
|---|---|
| **Strain** | *Chlorella vulgaris* UTEX 2714 |
| **Source** | UTEX Culture Collection of Algae, University of Texas at Austin |
| **URL** | https://utex.org/products/utex-2714 |
| **Format** | 15 mL liquid agar slant |
| **Cost** | ~$75 USD (academic pricing) |

### 2.2 Receiving & Storage

1. Upon receipt, store the slant at **4°C** in a refrigerator (NOT freezer).
2. Under ambient fluorescent light (no direct sunlight).
3. Viable for **6 months** at 4°C before passage is required.
4. Record in `STRAIN_REGISTRY.md`:
   - Date received
   - Lot number
   - Passage number (P0 if original)

---

## 3. Seed Culture Propagation

### 3.1 Flask Culture (2L)

**Materials:**
- [ ] Sterile 2L Erlenmeyer flask with foam plug
- [ ] 1L sterile BBM media (SOP-101)
- [ ] Inoculation loop or sterile pipette
- [ ] Orbital shaker or stir plate with magnetic bar
- [ ] Grow light (cool white LED, 100 µmol/m²/s)

**Procedure:**
1. Fill the 2L flask with **1L** of sterile BBM media.
2. Using aseptic technique (near a Bunsen burner or in a laminar flow hood):
   - Open the UTEX slant tube.
   - Transfer ~2 mL of liquid culture into the flask using a sterile pipette.
3. Cap with foam plug, wrap neck with parafilm.
4. Place on orbital shaker at **120 RPM** under continuous light.
5. Culture at **22–25°C** for **7–10 days**.
6. The culture should transition from pale green to **dark emerald green**.
7. Measure OD₆₈₀ daily — target: **≥ 0.5 AU** before proceeding.

### 3.2 Carboy Scale-Up (50L)

**Materials:**
- [ ] Clean 50L plastic carboy (food-grade HDPE)
- [ ] 40L sterile BBM media (SOP-101)
- [ ] Aquarium air pump with sterile airline tubing + airstone
- [ ] Flexible LED strip (continuous, 30% intensity)

**Procedure:**
1. Fill the carboy with **40L** of sterile BBM media.
2. Add the entire **1L** flask culture (giving a 1:40 dilution).
3. Insert a sterile airstone connected to an aquarium pump (set to gentle bubbling).
4. Wrap a flexible LED strip around the carboy exterior.
5. Culture for **10–14 days** at room temperature.
6. The culture should reach **OD₆₈₀ ≥ 0.8** (visually: opaque dark green).
7. This 50L seed is sufficient to inoculate a 19L garage reactor (giving ~2.5:1 dilution) or contribute to seeding the 1000L industrial vessel.

---

## 4. Main Reactor Inoculation

### 4.1 Pre-Inoculation Checklist

- [ ] Reactor vessel is clean (bleach-rinsed, water-rinsed, sterile media-filled)
- [ ] All sensors are connected and calibrated (pH, temperature)
- [ ] Camera is mounted and ROI is set (SOP: `calibration.py --roi-only`)
- [ ] CO₂ supply is connected but **valve is CLOSED**
- [ ] Pump is powered but **not running**
- [ ] LED array is powered but **at 0% duty cycle**

### 4.2 Inoculation Procedure

**Garage Profile (19L reactor):**
1. Transfer **5L** of the 50L seed culture into the reactor via gravity siphon.
2. Ensure the siphon tube is sterile (flame the tip or wipe with 70% ethanol).
3. Top up with sterile BBM to the **19L fill line**.
4. The initial cell density should be ~0.1–0.2 g/L (pale green, translucent).
5. Seal the reactor.

**Industrial Profile (1000L reactor):**
1. Transfer the entire 50L seed carboy via peristaltic pump into the vessel.
2. Top up with sterile media to the 850L fill line (leaving 15% headspace).
3. Initial cell density target: ~0.05 g/L.

### 4.3 Record in `STRAIN_REGISTRY.md`:
- Date of inoculation
- Seed batch ID
- Passage number (P1 if from original UTEX)
- Initial OD₆₈₀ reading
- Reactor fill volume

---

## 5. AI Nursery Mode Activation

### 5.1 Software Activation

Start the OpenCyclo OS. It will automatically enter `NURSERY` mode:

```bash
# From the reactor edge device:
sudo systemctl start opencyclo.service

# Or manually:
cd /opt/opencyclo
source venv/bin/activate
python main_loop.py
```

The Nursery state applies the following settings for **48 hours**:

| Parameter | Nursery Setting | Purpose |
|---|---|---|
| **LED** | Continuous (non-pulsing), 30% intensity | Gentle photon flux for fragile cells |
| **Pump** | Low speed (30% VFD / low relay duty) | Minimize shear on dilute culture |
| **CO₂** | PID active at pH 6.8 setpoint | Maintain optimal pH immediately |
| **Vision** | Sampling every 30s | Baseline density tracking |

### 5.2 Monitoring During Nursery (48h)

| Time | Check | Expected Observation |
|---|---|---|
| T+0h | System log | `STATE TRANSITION: IDLE → NURSERY` |
| T+2h | pH reading | Stable at 6.8 ± 0.2 |
| T+6h | Green/Red ratio | Slight increase from baseline |
| T+12h | Visual check | Culture should remain green, no settling |
| T+24h | OD₆₈₀ (manual) | Should show slight increase |
| T+48h | System log | `Nursery period complete. Transitioning to LOGARITHMIC_GROWTH` |

### 5.3 Post-Nursery Automatic Transition

After 48 hours, the OpenCyclo OS automatically transitions to
`LOGARITHMIC_GROWTH` mode:
- LED switches to **pulsed FLE mode** (50% duty cycle)
- Pump speed ramps to growth setting
- Vision sampling increases to every 5 seconds

**No operator intervention is required.** Monitor via the C.Y.C.L.O.S. HUD
or the terminal logs.

---

## 6. Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Culture turns yellow | Light stress or nutrient deficiency | Reduce LED to 20%, check media N:P |
| Culture settles/clumps | Insufficient mixing | Increase pump speed slightly |
| pH unstable / oscillating | PID gains too aggressive | Reduce Kp by 50%, see config.py |
| No growth after 48h | Dead inoculum or toxic media | Check microscopy; restart with fresh seed |

---

## 7. References

- Bold, H. C. (1949). *The morphology of Chlamydomonas chlamydogama.*
- UTEX Culture Collection Technical Guide: https://utex.org/pages/algal-culture-guide
