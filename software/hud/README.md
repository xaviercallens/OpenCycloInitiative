# 🤖 C.Y.C.L.O.S. Holographic HUD

The Heads-Up Display for the OpenCyclo OS running on edge nodes. Provides an industrial "Mission Control" or "Stark-Tech" aesthetic designed entirely in vanilla HTML/CSS/JS without React payloads.

## 🌐 Features
1. **Live WebSocket Bridges** `telemetry_bridge.js`: High-speed local binding to the Jetson Nano controller to stream live $\text{pH}, OD, k_L a, \text{and} \text{ RPM}$ updates straight to the UI.
2. **Dynamic Canvas Visualizations**:
    - Particle-based 2D Hologram.
    - Growth-curved plot tracing.
    - YOLOv8 bounding-box stream overlay.
3. **Web Audio SFX**: Synthesized UI feedback loops (`audio_sfx.js`):
    - Pump RPM mapping to frequency-oscillated background hums.
    - Blips and thuds for state transitions.

## 🔌 Running Locally
Just open `index.html` on your browser! The HUD works fully in 'SIMULATION' mode and automatically binds via WebSocket to the Edge Daemon when physically active.
