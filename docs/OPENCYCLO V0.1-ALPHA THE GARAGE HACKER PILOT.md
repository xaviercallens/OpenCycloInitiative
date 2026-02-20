# 🛠️ OPENCYCLO V0.1-ALPHA: THE "GARAGE HACKER" PILOT

### **Low-Tech, Upcycled Proof-of-Concept Bioreactor**

Before investing in a 1,000-Liter industrial build with CNC-machined polycarbonate and expensive sensor suites, it is highly recommended to validate the core physics (Rankine vortex, Flashing Light Effect) and software (Computer vision, pH-stat CO₂ control) on a workbench scale.

The **OpenCyclo V0.1 "Garage Edition"** is a functional 19-Liter (5-gallon) prototype. Built entirely from upcycled household items, cheap aquarium hardware, and standard maker electronics, this benchtop unit proves that the industrial physics and AI logic work perfectly at a 1:50 scale. You can build it over a weekend for under €150 / $150.

---

## 🛒 1. THE SCAVENGER BILL OF MATERIALS (BOM)

### **A. The Vessel (Industrial Cylinder  Upcycled Water Jug)**

* **The Reactor Body:** 1x Standard **19-Liter (5-gallon) clear PET water cooler jug**.
* *The Hack:* You will invert it! When flipped upside down, the sloped neck forms the exact 60-degree hydrodynamic cone needed to prevent dead zones where algae settle and rot.


* **The Stand:** A simple wooden box, or an upcycled bar stool with a hole cut in the seat to hold the inverted jug securely.

### **B. Fluidics (VFD Pump  12V Aquarium Pump)**

* **The Pump:** 1x **12V DC Brushless Water Pump** (approx. 800–1200 L/hr, used for aquariums or solar fountains). *Safety Warning: Do not use a 110V/220V AC washing machine pump; they leak, present a shock hazard, and have high mechanical shear that will shred the algae cells.*
* **Plumbing:** 2 meters of clear vinyl tubing (1/2 inch) and hose clamps.
* **The Vortex Injector:** 1x Plastic bulkhead fitting (1/2 inch) and 1x 90-degree PVC elbow.

### **C. Gas Exchange (Industrial SiC Sparger  Limewood Airstone)**

* **The Sparger:** 1x **Limewood (Basswood) Airstone**. Used in marine aquarium protein skimmers, wood has natural microscopic parallel pores that create incredibly fine microbubbles, mimicking industrial sintered ceramics for about $5.
* **CO₂ Source:**
* *Ultra-Low Tech:* A DIY 2-Liter soda bottle filled with warm water, sugar, and baker's yeast (naturally ferments bio-CO₂ for weeks).
* *Mid-Tech:* A SodaStream cylinder with a cheap aquarium CO₂ regulator.


* **The Valve:** 1x 12V normally-closed (NC) plastic aquarium CO₂ solenoid valve.

### **D. Illumination & AI Edge-Compute**

* **Lighting:** 1x Roll (5 meters) of 12V LED "Grow Light" strip (Red/Blue 4:1 alternating diodes).
* **Compute Node:** Any **Raspberry Pi** (3, 4, 5, or Zero 2 W) or an old laptop running Linux.
* **Microcontroller/Relay:** 1x Arduino Uno or ADS1115 ADC module (to convert analog sensor signals for the Pi) and 1x 5V Relay module.
* **Sensors:** 1x generic Arduino-compatible analog pH sensor kit (e.g., DF-Robot) and 1x Standard USB 1080p Webcam (e.g., Logitech C270).

---

## 🔧 2. GARAGE CONSTRUCTION PLAN

### **Step 1: Hack the Vessel (The Upside-Down Jug)**

1. Take the 19L water jug and flip it upside down. The original dispensing neck is now your bottom drain.
2. Carefully cut a large 15cm (6-inch) circular hole in the *new top* (the flat bottom of the jug) to allow access for your sensors, sparger, and gas exhaust.
3. Place the inverted jug into your wooden stand/stool so the neck hangs freely underneath.

### **Step 2: Plumb the Cyclonic Vortex**

1. **Bottom Drain:** Attach a flexible hose to the neck of the jug. Seal it tightly with a hose clamp. Route this hose to the **inlet** of your 12V pump.
2. **Tangential Inlet (The Secret to the Vortex):** Drill a hole in the side of the jug, about 1/3 of the way up from the neck. Insert the bulkhead fitting. On the *inside* of the jug, attach the 90-degree PVC elbow.
3. **Angle the elbow so it points horizontally *along the inside curved wall* of the jug.** Connect the pump output to this inlet.
4. *Validation:* Fill with tap water and turn the pump on. The water will shoot along the wall, creating a perfect, continuous mini-tornado (Rankine vortex) down the cone.

### **Step 3: Illumination & Sparging**

1. **The Flashing Light Effect:** Wrap the 12V LED grow light strip tightly around the *outside* of the clear jug in a spiral. Because the jug is narrow, the external light penetrates well. The vortex will violently spin the algae from the bright LED wall to the darker center, replicating the industrial flashing light effect.
2. Drop the Limewood CO₂ diffuser through the top hole so it rests exactly at the bottom of the neck. Connect it to your 12V CO₂ solenoid, then to your CO₂ source.

---

## 💻 3. SOFTWARE & AI VALIDATION (OPENCYCLO LITE)

You don't need heavy Docker containers or YOLO models for the garage. You can write three simple Python scripts to prove the industrial logic.

### **Test A: The pH-Stat Loop (Automated Carbon Feeding)**

1. Suspend the cheap pH probe in the water. Wire the 12V CO₂ solenoid to your relay module, connected to the Pi/Arduino.
2. **The Logic:** Write a simple Python loop reading the pH.
* As algae photosynthesize, the water becomes basic.
* When `pH > 7.5`, the Pi fires the relay. The solenoid opens (or the yeast gas is released), microbubbles fill the vortex, and carbonic acid forms.
* When `pH < 6.8`, the relay clicks off. *You have just validated automated, zero-waste direct carbon absorption.*



### **Test B: The Computer Vision "Soft Sensor"**

1. Mount the USB webcam on a stick, staring directly at the side of the spinning jug. *Tip: Tape a piece of plain white paper on the back of the jug so the camera has a consistent white background.*
2. **The Script:** Write a short OpenCV (`cv2`) Python script that captures a frame every 10 minutes, masks the background, and extracts the average "Green" saturation channel (HSV color space).
3. Over 5 to 7 days, watch the script plot a perfect logarithmic growth curve on your screen as the water turns from faint green to dark, opaque emerald.

### **Test C: PWM Light Pulsing (Energy Saving)**

Wire the LEDs through a logic-level MOSFET connected to an Arduino PWM pin. Write a script to blink the LEDs at 50 Hz (10ms ON, 10ms OFF). To your eye, the lights look solid. To your electricity meter, you just cut power consumption by 50% without slowing algae growth!

---

## 🧫 4. GARAGE BIOLOGY (THE WETWARE)

You don't need industrial wastewater or a sterile lab. You can hack the biology safely at home.

**1. The "Clean" Nutrient Media:**
Fill the jug with 15 Liters of tap water. **CRUCIAL:** You must add an aquarium dechlorinator (e.g., Seachem Prime) or let the water sit in an open bucket for 24 hours. *Chlorine will kill algae instantly.*
Add:

* 15 mL of standard liquid hydroponic fertilizer (like *General Hydroponics Flora* series) or a heavily diluted liquid houseplant food (N-P-K).
* 1/2 teaspoon of Epsom salts (Magnesium sulfate—vital for building the central atom of the chlorophyll molecule).

**2. The Starter Strain:**
Buy a live culture of **Chlorella vulgaris** or **Spirulina** online. It is commonly sold on educational science supply sites (like Carolina Biological), or on Amazon/eBay as "Live Phytoplankton" or "Green Water" for feeding aquarium corals.

**3. The Run:**
Pour 500mL of the live green culture into your spinning 15L jug. Turn on the LEDs and launch the Python scripts.

---

## 🎯 5. SUCCESS METRICS & HARVESTING

By spending a weekend in the garage, you will successfully:

1. **Prove the Vortex Physics:** Watch how centrifugal force naturally prevents the algae from sticking to the walls (biofouling), eliminating the need for mechanical wipers.
2. **Capture Actual CO₂:** Weigh your SodaStream bottle before and after a 2-week run. You will see a measurable drop in CO₂ mass, directly converted into the thick green slurry in your jug.

**The Harvest:**
After 7 to 10 days, turn off the pump. Because you inverted the jug, the heavy, carbon-dense algae will naturally settle into the neck over 12 hours. Siphon this thick paste out, spread it on a tray, and dry it in the sun. Weigh the dried green flakes.

**Multiply that dry weight by 1.83 — that is exactly how much CO₂ your garage just permanently removed from the atmosphere.**

Once this dark green, AI-managed 15L vortex is humming on your workbench, you have mastered the foundational science. You are now ready to download the CAD files, order the Polycarbonate, and scale up to the 1,000-Liter OpenCyclo system (using the algae from this pilot as your seed culture!).