# 🧠 OpenCyclo OS (C.Y.C.L.O.S.)

The C.Y.C.L.O.S. (Cognitive Yield & Carbon Logistics Operating System) is the central Python-based edge daemon. Designed to run on a Jetson Nano or Raspberry Pi 5, this service translates high-level state decisions into physical actions for the CV-PBR-V1 hardware.

## 🚀 Key Modules
1. **`main_loop.py`**: The master state machine. Handles transitions from `NURSERY` ➔ `LOGARITHMIC_GROWTH` ➔ `STEADY_STATE_TURBIDOSTAT` based on sensory inputs.
2. **`config.py`**: The definitive truth for all constants, limits, PID terms, and hardware GPIO mappings.
3. **`led_pwm_sync.py`**: Calculates the precise frequency for the Flash Light Effect (FLE) array by locking PWM duty cycles to the vortex angular velocity.
4. **`ph_stat_co2.py`**: A PID controller that manages the CO₂ solenoid to hold pH 6.8 with 0.1 variance, avoiding pH-shock.
5. **`vision_density.py`**: A soft-sensor utilizing OpenCV to derive optical density (`g/L`) from Green/Red ratios.
6. **`telemetry_api.py`**: The high-speed WebSocket + REST interface that broadcasts live reactor data to the HUD and reality-sync nodes.

## ⚙️ Installation & Operation
```bash
# Provisioning the OS
cd deploy
sudo ./setup.sh

# Starting the main loop
python3 main_loop.py
```

## 🧪 Testing State
This daemon is fortified with comprehensive unit and integration tests under `/tests/`. It mocks physical GPIO reads, meaning `main_loop.py` can be heavily optimized without requiring massive wet-runs. All State Machine transition rules have been validated.
