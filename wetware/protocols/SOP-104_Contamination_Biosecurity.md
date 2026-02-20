# SOP-104: Contamination Response & pH Shock Biosecurity Protocol

> **OpenCyclo Initiative** | Standard Operating Procedure  
> **Version:** 0.1-alpha  
> **License:** OpenMTA  
> **CRITICAL SAFETY PROCEDURE — Read entirely before execution**

---

## 1. Scope

This procedure defines the response protocol when biological contamination
(predatory zooplankton or biofilm) is detected in the bioreactor culture.

The primary countermeasure is the **pH Shock** — a controlled, rapid acidification
of the culture to pH 4.5 for 4 hours, which kills predators (*Brachionus* rotifers,
ciliates) while *Chlorella vulgaris* survives due to its acid-tolerant cell wall.

---

## 2. Detection Methods

### 2.1 Automated (AI Vision — `vision_density.py`)

The OpenCyclo OS runs a YOLOv8 biosecurity model every 10th frame.
When contamination is detected (confidence ≥ 85%):

1. A **webhook alert** is sent to the operator.
2. The terminal log displays: `[BIOSECURITY] THREAT DETECTED: BRACHIONUS`
3. The C.Y.C.L.O.S. HUD shows a crimson targeting reticle.
4. **The system does NOT auto-trigger pH Shock.** Operator confirmation is required.

### 2.2 Manual (Microscopy)

| Indicator | What to look for |
|---|---|
| **Rotifers** | 100–500 µm organisms with cilia "wheels" at the head. Active swimmers. |
| **Ciliates** | 50–200 µm single-celled organisms with hair-like cilia covering the body. |
| **Biofilm** | Slimy deposits on reactor walls, especially near the waterline (headspace). |
| **Culture crash** | Rapid decrease in OD₆₈₀ / green ratio without harvest. pH rising above 7.5. |

**Microscopy checklist:**
- [ ] Take a 1 mL sample from the reactor
- [ ] Place on a glass slide with coverslip
- [ ] Examine at 40x and 100x magnification
- [ ] Photograph any suspicious organisms
- [ ] Compare against the reference images in `wetware/references/predators/`

---

## 3. pH Shock Procedure

### 3.1 Prerequisites

- [ ] Confirm contamination via at least ONE of: AI detection (≥85%), microscopy, or rapid OD crash
- [ ] Ensure CO₂ supply is sufficient for 4+ hours of continuous dosing
- [ ] Verify pH probe is recently calibrated (within 7 days)
- [ ] Close any media top-up valves (isolate the reactor)

### 3.2 Execution

#### Automated (Software-Triggered)

```bash
# From the OpenCyclo OS CLI or API:
# This triggers PHStatController.override_ph_shock()
python -c "
import asyncio
from ph_stat_co2 import PHStatController
async def shock():
    ctrl = PHStatController()
    await ctrl.initialize()
    await ctrl.override_ph_shock(target_ph=4.5, hold_hours=4)
asyncio.run(shock())
"
```

The controller will:
1. **Phase 1 — Drive Down** (~10–30 min): Open CO₂ valve at 100% to drive pH from ~6.8 → 4.5.
2. **Phase 2 — Hold** (4 hours): Maintain pH at 4.5 ± 0.1 using PID control.
3. **Phase 3 — Restore** (~30 min): Gradually restore pH to 6.8 by closing the CO₂ valve and allowing algal photosynthesis to raise pH naturally.

#### Manual (Garage Profile — No Automation)

1. Disconnect the pH controller.
2. Open the CO₂ regulator fully to the sparger.
3. Monitor pH with a handheld meter every 5 minutes.
4. When pH reaches **4.5**, reduce CO₂ flow to a trickle (just enough to maintain).
5. Start a timer for **4 hours**.
6. After 4 hours, close CO₂ completely.
7. Wait for pH to naturally rise above 6.0 (may take 2–6 hours).
8. Reconnect the pH controller.

### 3.3 Post-Shock Monitoring (48-hour Recovery Window)

| Time | Action | Expected |
|---|---|---|
| T+0h | Shock complete, valve closed | pH slowly rising |
| T+2h | Sample for microscopy | Dead rotifers visible (no movement) |
| T+6h | pH probe reading | pH should be > 5.5 |
| T+12h | pH probe reading | pH should be > 6.0 |
| T+24h | OD₆₈₀ / green ratio | Should stabilize or begin recovery |
| T+48h | Full assessment | Culture should be growing again |

---

## 4. Escalation — Culture Does Not Recover

If after 48 hours the culture shows NO signs of recovery (OD continues falling,
pH remains high, no green coloration):

### 4.1 Assessment

- [ ] Confirm pH shock actually reached 4.5 (check pH logs)
- [ ] Confirm shock duration was 4 hours (check logs)
- [ ] Examine under microscope — are predators still alive?
- [ ] Test media nutrient levels (N, P may be depleted)

### 4.2 Recovery Options

| Option | When to use |
|---|---|
| **Repeat pH shock** | If predators survived (rare for *Chlorella*-adapted rotifers) |
| **Partial media replacement** | If nutrients are depleted — replace 50% of volume with fresh BBM |
| **Full restart** | If culture is irreversibly crashed — drain, clean, re-inoculate from seed stock |

### 4.3 Full Restart Procedure

1. Drain reactor completely.
2. Flush with 10% bleach solution, hold for 1 hour.
3. Rinse with 3 volumes of clean water.
4. Rinse with sterile RO water.
5. Refill with fresh sterile media (SOP-101).
6. Re-inoculate from seed carboy (SOP-102).
7. Enter NURSERY mode (48h acclimation).

---

## 5. Safety Warnings

| ⚠️ Hazard | Mitigation |
|---|---|
| CO₂ gas is an asphyxiant | Ensure the reactor room has CO₂ monitoring and ventilation |
| Acidified culture is corrosive | Wear gloves and eye protection when handling |
| Pressure buildup | Ensure degassing port is open during CO₂ flooding |
| Electrical shock | Do not touch electrical components (relay, VFD) with wet hands |

---

## 6. Record Keeping

Log the following for every pH Shock event:

```
Date: ___________
Time Start: ___________
Time End: ___________
Trigger: [ ] AI Detection  [ ] Microscopy  [ ] OD Crash  [ ] Other
Target pH reached: ___________
Hold duration: ___________
Recovery confirmed at T+___h
Operator: ___________
Notes: ___________
```

---

## 7. References

- Wang, H., et al. (2013). *pH-based control of Chlorella against rotifer contamination.* Bioresource Technology.
- Richmond, A. (2013). *Handbook of Microalgal Culture.* Wiley-Blackwell.
