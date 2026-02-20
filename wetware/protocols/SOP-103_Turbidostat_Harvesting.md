# SOP-103: Turbidostat Harvesting Procedure

> **OpenCyclo Initiative** | Standard Operating Procedure  
> **Version:** 0.1-alpha  
> **License:** OpenMTA

---

## 1. Scope

This procedure defines the semi-continuous harvesting of algal biomass
from the bioreactor when the culture reaches the target density threshold.

Two modes:
- **Garage Profile:** Manual siphon harvest (gravity-based)
- **Industrial Profile:** Automated turbidostat via 3-way valve + hydrocyclone

---

## 2. Harvest Trigger

### 2.1 Density Threshold

| Profile | Trigger Density | Detection Method |
|---|---|---|
| Garage | **≥ 4.0 g/L** (dry weight) | Vision sensor green/red ratio + manual OD₆₈₀ |
| Industrial | **≥ 6.0 g/L** (dry weight) | Vision sensor (calibrated polynomial) |

When `vision_density.py` reports the density at or above the trigger:
- **Garage:** The terminal and HUD display: `🌿 HARVEST READY`
- **Industrial:** The system automatically opens the harvest valve

### 2.2 Visual Indicators

| Green/Red Ratio | Approximate Density | Culture Appearance |
|---|---|---|
| 1.0 – 1.3 | 0.1 – 0.5 g/L | Pale green, translucent |
| 1.3 – 1.8 | 0.5 – 2.0 g/L | Medium green, slightly opaque |
| 1.8 – 2.5 | 2.0 – 4.0 g/L | Dark green, opaque |
| 2.5+ | 4.0+ g/L | Very dark, almost black-green |

---

## 3. Garage Profile — Manual Siphon Harvest

### 3.1 Materials

- [ ] 5L collection bucket (food-grade)
- [ ] Sterile silicone tubing (8mm ID)
- [ ] Tube clamp
- [ ] Fresh sterile BBM media (SOP-101) — volume equal to harvest

### 3.2 Procedure

1. **Stop the pump** (turn off relay or unplug).
2. **Wait 12 hours** for the culture to stratify in the reactor neck.
   - Dense biomass will settle into the narrowing cone/neck region.
   - The clear supernatant rises to the top.
3. **Siphon the concentrated paste:**
   - Insert the sterile tube into the reactor neck (bottom 20%).
   - Start siphon by priming the tube.
   - Collect **3–5L** of concentrated algal paste into the bucket.
   - Clamp the tube when done.
4. **Top up with fresh media:**
   - Add an equal volume of fresh sterile BBM to restore the reactor volume.
5. **Restart the pump.**
6. The OpenCyclo OS will automatically detect the density drop and
   remain in `STEADY_STATE_TURBIDOSTAT` or transition back to
   `LOGARITHMIC_GROWTH` if density falls below threshold.

### 3.3 Biomass Processing (Garage Scale)

| Route | Method | Product |
|---|---|---|
| **Drying** | Spread on trays, fan-dry at 40°C for 48h | Dried algae flakes |
| **Biochar** | Dry, then pyrolyze in a kiln at 350–500°C | Soil amendment |
| **Composting** | Mix wet paste with garden compost | Organic fertilizer |

---

## 4. Industrial Profile — Automated Turbidostat

### 4.1 System Components

| Component | Specification |
|---|---|
| 3-Way Motorized Ball Valve | 1.5" Tri-Clamp, 24V actuator |
| Hydrocyclone | 100mm body diameter (OQ-5 geometry — see Engineering Resolution) |
| High-Pressure Pump | 3 Bar inlet pressure to hydrocyclone |
| Clarified Return Line | Overflow from hydrocyclone vortex finder |
| Fresh Media Supply | Peristaltic pump from media reservoir |

### 4.2 Automated Sequence

When `vision_density.py` reports density ≥ trigger:

```
1. [main_loop.py] → Opens 3-way valve to HARVEST position
2. [main_loop.py] → Diverts 15% of reactor volume (150L) through hydrocyclone
3. [hydrocyclone]  → Separates culture into:
   - UNDERFLOW: ~5L of thick algal paste (20-30% solids)
   - OVERFLOW: ~145L of clarified water (returned to reactor)
4. [main_loop.py] → Closes 3-way valve
5. [main_loop.py] → Opens fresh media supply valve
6. [main_loop.py] → Draws 5L of fresh sterile media to restore volume
7. [main_loop.py] → Logs harvest event with timestamp and density data
```

### 4.3 Volume Balance

| Stream | Volume | Destination |
|---|---|---|
| **Harvest diversion** | 150L (15% of 1000L) | Hydrocyclone inlet |
| **Concentrated paste** | ~5L (3-5% of diversion) | Collection tank → downstream |
| **Clarified return** | ~145L | Back to reactor |
| **Fresh media makeup** | ~5L | From media reservoir |
| **Net volume change** | 0L | Reactor level maintained |

---

## 5. Downstream Biomass Routing

### 5.1 Hydrothermal Liquefaction (HTL) — Bio-Oil

- Feed wet algal paste (no drying required) into a continuous
  HTL reactor at 300°C / 200 Bar.
- Produces: bio-crude oil (~35% yield by dry weight) + aqueous phase (recycle N/P).

### 5.2 Pyrolysis — Biochar (Carbon Sequestration)

- Dry the paste to <10% moisture.
- Slow pyrolysis at 450°C for 2 hours in an oxygen-free retort.
- Produces: **biochar** with >50% fixed carbon.
- Apply to agricultural soil at 10–20 tonnes/hectare.
- **Carbon permanence:** >1000 years (recalcitrant carbon pool).
- This is the **Planetary Symbiotic Cycle (PSC)** carbon sink pathway.

### 5.3 Direct Application — Soil Amendment

- Mix wet paste directly with compost.
- Apply as organic fertilizer + soil conditioner.
- Lower carbon permanence than biochar but simpler.

---

## 6. Record Keeping

Log for every harvest event:

```
Date: ___________
Time: ___________
Density at trigger: _____ g/L
Volume harvested: _____ L
Paste collected: _____ L
Fresh media added: _____ L
Post-harvest density: _____ g/L
Downstream route: [ ] HTL  [ ] Pyrolysis  [ ] Compost  [ ] Other
Operator: ___________
```

---

## 7. References

- Molina Grima, E., et al. (2003). *Recovery of microalgal biomass and metabolites.*
  Biotechnology Advances, 20(7-8), 491-515.
- Bradley, D. (1965). *The Hydrocyclone.* Pergamon Press. (Proportions used for harvester geometry)
