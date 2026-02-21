# 🧪 OpenCyclo OS Unit Testing Coverage

The `opencyclo_os` relies heavily on hardware interactions, states, and PID controllers. As of **v1.0.0+**, we have established a baseline mocking structure and automated tests via `pytest` and `pytest-asyncio`.

## 📊 Current Coverage Metrics (42% Overall)

| Module | Coverage % | Status | Notes |
|---|---|---|---|
| `config.py` | 100% | ✅ Excellent | Fully tested boundary limits and config loading. |
| `vision_density.py` | 68% | 🟡 Good | Missing coverage on raw camera hardware failures. Core OpenCV algorithms tested. |
| `ph_stat_co2.py` | 56% | 🟡 Good | Missing coverage on Modbus/I2C real hardware callbacks. Core PID and State tested. |
| `utils/logger.py` | 42% | 🟠 Needs Work | Basic tests only. |
| `utils/webhook.py` | 32% | 🟠 Needs Work | |
| `led_pwm_sync.py` | 0% | 🔴 Missing | Action Item: Add tests for frequency/duty cycle math. |
| `main_loop.py` | 0% | 🔴 Missing | Action Item: Needs exhaustive coverage on state machine transitions. |
| `state_persistence.py` | 0% | 🔴 Missing | Action Item: Missing tests for JSON disk saves/loads. |
| `telemetry_api.py` | 0% | 🔴 Missing | Action Item: FastAPI and WebSockets endpoints lack automated testing. |

## 🚀 Running Tests
Required dependencies:
```bash
pip install pytest pytest-cov pytest-asyncio fake-rpi
```

Run test suite with coverage report:
```bash
python -m pytest --cov=.
```

## 🛠️ Next Steps for Testing
To push coverage above our 80% target:
1.  **State Persistence:** Write a suite to test corrupt JSON recovery logic.
2.  **Telemetry API:** Use `pytest.mark.asyncio` combined with FastAPI's `TestClient` to test the WebSocket broadcasts.
3.  **LED Sync:** Provide mocked CFD angular velocity inputs and verify the resulting `Hz` math without running the GPIO.
4.  **Main Loop:** Implement a robust test harness using `fake-rpi` and pre-populated state dictionaries to simulate an entire 7-day run in milliseconds.
