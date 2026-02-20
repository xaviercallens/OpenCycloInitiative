# SOP-101: Media Formulation & Sterilization

> **OpenCyclo Initiative** | Standard Operating Procedure  
> **Version:** 0.1-alpha (Garage Profile)  
> **License:** OpenMTA  
> **Organism:** *Chlorella vulgaris* (UTEX 2714)

---

## 1. Scope

This procedure covers the preparation, sterilization, and quality control of
growth media for the OpenCyclo bioreactor. Two media formulations are defined:

| Media Type | Use Case | Composition |
|---|---|---|
| **BBM (Bold's Basal Medium)** | Garage prototype, lab validation | Defined synthetic salts |
| **Wastewater-Digestate Blend** | Industrial production, circular economy | Pre-treated anaerobic digestate + municipal wastewater |

The **Garage Profile** uses BBM for simplicity and reproducibility.

---

## 2. Required Materials

### 2.1 BBM Stock Solutions

| Stock | Salt | Concentration (g/L stock) | mL stock per L media |
|---|---|---|---|
| 1 | NaNO₃ | 25.0 | 10 |
| 2 | CaCl₂·2H₂O | 2.5 | 10 |
| 3 | MgSO₄·7H₂O | 7.5 | 10 |
| 4 | K₂HPO₄ | 7.5 | 10 |
| 5 | KH₂PO₄ | 17.5 | 10 |
| 6 | NaCl | 2.5 | 10 |

### 2.2 Trace Metal Solution

| Component | Amount per L stock |
|---|---|
| Na₂EDTA | 50.0 g |
| FeSO₄·7H₂O | 4.98 g |
| ZnSO₄·7H₂O | 8.82 g |
| MnCl₂·4H₂O | 1.44 g |
| MoO₃ | 0.71 g |
| CuSO₄·5H₂O | 1.57 g |
| Co(NO₃)₂·6H₂O | 0.49 g |
| H₃BO₃ | 11.42 g |

Add **1 mL** of trace metal stock per liter of final media.

### 2.3 Equipment

- [ ] Autoclave or pressure cooker (121°C / 15 psi)
- [ ] UV-C sterilization lamp (dose: **40 mJ/cm²** — OQ-8 resolved)
- [ ] Bag filter housing with **5 µm** polypropylene cartridge (OQ-8 resolved)
- [ ] pH meter (calibrated)
- [ ] Analytical balance (0.01g resolution)
- [ ] 1L graduated cylinders, volumetric flasks

---

## 3. Procedure

### 3.1 BBM Preparation (Garage Profile — 19L batch)

1. **Prepare stock solutions** (can be stored at 4°C for 6 months):
   - For each stock (1–6), dissolve the salt in 1L of distilled water.
   - Prepare the trace metal solution separately.

2. **Mix the media:**
   - Fill a clean 20L carboy with **18.7L** of distilled or RO water.
   - Add **190 mL** of each stock solution (1–6).
   - Add **19 mL** of trace metal solution.
   - Mix thoroughly with a magnetic stir bar for 10 minutes.

3. **Adjust pH:**
   - Measure pH (should be ~6.4–6.6 for unbuffered BBM).
   - Adjust to **pH 6.8 ± 0.2** using 1M NaOH or 1M HCl dropwise.

4. **Sterilize:**
   - **Option A (Autoclave):** Autoclave at 121°C for 20 minutes. Cool to room temperature before use.
   - **Option B (Filter + UV-C):** For heat-sensitive setups, pass through a **0.2 µm** membrane filter, then expose to UV-C at **40 mJ/cm²**.

5. **Store:**
   - Sterile media can be stored at 4°C for up to 2 weeks.
   - Label with: date, batch ID, pH, volume.

### 3.2 Wastewater-Digestate Blend (Industrial Profile — 1000L batch)

> ⚠️ **This procedure requires biological safety precautions (BSL-1 minimum).**

1. **Source:** Obtain pre-settled anaerobic digestate supernatant from a municipal WWTP.
2. **Pre-filter:** Pass through **5 µm bag filter** to remove particulates.
3. **UV-C Sterilize:** Flow through inline UV-C reactor at **40 mJ/cm²** dose.
4. **Characterize:**
   - Measure: Total N, Total P, COD, pH, conductivity.
   - Target N:P molar ratio: **16:1** (Redfield ratio for green algae).
   - If N-deficient, supplement with NH₄Cl or urea.
   - If P-deficient, supplement with KH₂PO₄.
5. **Adjust pH to 6.8 ± 0.2** with CO₂ sparging or NaOH.

---

## 4. Quality Control Checklist

| Parameter | Target | Method | Pass? |
|---|---|---|---|
| pH | 6.8 ± 0.2 | pH probe | ☐ |
| Turbidity | < 10 NTU | Visual / turbidimeter | ☐ |
| N:P ratio | ~16:1 (mol/mol) | Spectrophotometric | ☐ |
| Sterility | No growth at 48h | Agar plate streaking | ☐ |
| Temperature | 20–25°C | Thermometer | ☐ |

---

## 5. Waste Disposal

- Unused media: Neutralize pH to 6.5–7.5, dispose via sanitary drain.
- Contaminated media: Autoclave at 121°C for 30 min, then drain.

---

## 6. References

- Bischoff, H. W., & Bold, H. C. (1963). *Some soil algae from Enchanted Rock.*
- UTEX Culture Collection: https://utex.org/products/utex-2714
