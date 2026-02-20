"""
CycloTwin SITL — ROS 2 Virtual Hardware Bridge
=================================================

Implements a Software-In-The-Loop (SITL) bridge between the OpenCyclo
Python OS and the CycloTwin physics engine.

Architecture:
  ┌──────────────────┐     ROS 2 Topics      ┌──────────────────┐
  │  OpenCyclo OS     │ ──────────────────────▶ │  PINN Engine     │
  │  (main_loop.py)   │     /cmd_co2_valve     │  (modulus_rt.py) │
  │                   │     /cmd_pump_speed     │                  │
  │                   │     /cmd_led_pwm        │                  │
  │                   │ ◀────────────────────── │                  │
  │                   │     /sensor_ph          │                  │
  │                   │     /sensor_density     │                  │
  │                   │     /sensor_temperature │                  │
  └──────────────────┘                         └──────────────────┘

The bridge intercepts the OpenCyclo OS hardware calls (GPIO, I2C, SPI)
and converts them into ROS 2 messages that the PINN simulator consumes.

Spec reference: Digital Twin Specification §6
                CycloTwin Implementation Guide §5.1
"""

import asyncio
import json
import time
import math
from dataclasses import dataclass, field
from typing import Optional, Callable

# We use a lightweight pub/sub abstraction that works both with real ROS 2
# and a standalone mock for environments without ROS 2.

try:
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import Float64, Bool, String
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False


# ──────────────────────────────────────────────
# Virtual Hardware State
# ──────────────────────────────────────────────

@dataclass
class VirtualHardwareState:
    """Represents the virtual reactor's physical state."""
    # Actuator commands (from OpenCyclo OS)
    co2_valve_open: bool = False
    pump_speed_pct: float = 0.0
    led_pwm_freq_hz: float = 82.5
    led_duty_pct: float = 50.0
    harvest_valve_open: bool = False

    # Sensor readings (from PINN / physics model)
    ph: float = 6.8
    density_g_l: float = 0.1
    temperature_c: float = 24.0
    dissolved_o2_pct: float = 85.0
    dissolved_co2_mg_l: float = 0.5
    vortex_rpm: float = 0.0

    # Internal physics state
    _biomass_integral: float = 0.0
    _time: float = 0.0


class SimplifiedPhysicsModel:
    """
    Lightweight physics model for SITL when the full PINN is not available.

    This provides a reasonable approximation of reactor dynamics using
    simple ODEs, enabling end-to-end testing of the OpenCyclo OS without
    any GPU or heavy compute.

    Equations:
      pH:  dpH/dt = -k_co2 * valve_state + k_photo * density
      density: dD/dt = mu_max * D * (1 - D/D_max) * light_factor - harvest_rate
      temperature: dT/dt = k_heat * (T_env - T) + k_pump * pump_speed²
    """

    def __init__(self):
        self.state = VirtualHardwareState()
        self._last_update = time.time()

        # Physical constants
        self.k_co2_ph = 0.15        # pH drop rate from CO₂ valve (pH/s)
        self.k_photo_ph = 0.02      # pH rise from photosynthesis (pH/s/g/L)
        self.mu_max = 0.06          # Max specific growth rate (1/h → /3600 for /s)
        self.d_max = 8.0            # Carrying capacity (g/L)
        self.k_heat = 0.001         # Thermal diffusion rate (1/s)
        self.t_env = 22.0           # Ambient temperature (°C)
        self.k_pump_heat = 0.0005   # Heat generation from pump friction

    def step(self, dt: Optional[float] = None) -> VirtualHardwareState:
        """
        Advance the physics simulation by dt seconds.

        Args:
            dt: Time step in seconds. If None, uses wall clock delta.

        Returns:
            Updated VirtualHardwareState
        """
        now = time.time()
        if dt is None:
            dt = now - self._last_update
        self._last_update = now
        s = self.state

        # ── pH dynamics ──
        co2_effect = -self.k_co2_ph * (1.0 if s.co2_valve_open else 0.0)
        photo_effect = self.k_photo_ph * s.density_g_l * (s.led_duty_pct / 100.0)
        # Natural buffering: pH drifts toward 7.0 slowly
        buffer_effect = 0.005 * (7.0 - s.ph)
        s.ph += (co2_effect + photo_effect + buffer_effect) * dt
        s.ph = max(3.0, min(10.0, s.ph))

        # ── Biomass growth ──
        # Light factor: depends on LED duty cycle and pump creating vortex flow
        pump_factor = min(s.pump_speed_pct / 50.0, 1.0)  # Normalize to optimal 50%
        light_factor = (s.led_duty_pct / 100.0) * pump_factor
        # Optimal pH range bonus
        ph_factor = max(0, 1.0 - abs(s.ph - 6.8) / 2.0)
        # Logistic growth
        growth = (self.mu_max / 3600.0) * s.density_g_l * (1 - s.density_g_l / self.d_max)
        growth *= light_factor * ph_factor
        # Harvest loss
        harvest_loss = 0.5 * s.density_g_l * (1.0 if s.harvest_valve_open else 0.0)
        s.density_g_l += (growth - harvest_loss) * dt
        s.density_g_l = max(0.001, s.density_g_l)

        # ── Temperature ──
        cooling = self.k_heat * (self.t_env - s.temperature_c)
        pump_heat = self.k_pump_heat * (s.pump_speed_pct / 100.0) ** 2
        s.temperature_c += (cooling + pump_heat) * dt
        s.temperature_c = max(10.0, min(40.0, s.temperature_c))

        # ── Vortex RPM ──
        # Approximate: RPM = pump_speed * 68 (at 100% = 6800 RPM max)
        target_rpm = s.pump_speed_pct * 68.0
        s.vortex_rpm += (target_rpm - s.vortex_rpm) * 0.1  # Inertia smoothing

        # ── Dissolved CO₂ ──
        if s.co2_valve_open:
            s.dissolved_co2_mg_l = min(20.0, s.dissolved_co2_mg_l + 0.5 * dt)
        else:
            s.dissolved_co2_mg_l = max(0.0, s.dissolved_co2_mg_l - 0.1 * dt)

        s._time += dt
        return s


# ──────────────────────────────────────────────
# ROS 2 Node Implementation
# ──────────────────────────────────────────────

if ROS2_AVAILABLE:
    class VirtualHardwareBridgeNode(Node):
        """
        ROS 2 node that bridges OpenCyclo OS commands to SITL physics.
        """

        def __init__(self):
            super().__init__('virtual_hardware_bridge')
            self.physics = SimplifiedPhysicsModel()

            # ── Subscribe to actuator commands ──
            self.sub_co2 = self.create_subscription(
                Bool, '/cmd_co2_valve', self._on_co2_valve, 10)
            self.sub_pump = self.create_subscription(
                Float64, '/cmd_pump_speed', self._on_pump_speed, 10)
            self.sub_led_freq = self.create_subscription(
                Float64, '/cmd_led_pwm_freq', self._on_led_freq, 10)
            self.sub_led_duty = self.create_subscription(
                Float64, '/cmd_led_duty', self._on_led_duty, 10)
            self.sub_harvest = self.create_subscription(
                Bool, '/cmd_harvest_valve', self._on_harvest_valve, 10)

            # ── Publish sensor readings ──
            self.pub_ph = self.create_publisher(Float64, '/sensor_ph', 10)
            self.pub_density = self.create_publisher(Float64, '/sensor_density', 10)
            self.pub_temp = self.create_publisher(Float64, '/sensor_temperature', 10)
            self.pub_rpm = self.create_publisher(Float64, '/sensor_vortex_rpm', 10)
            self.pub_state = self.create_publisher(String, '/reactor_state', 10)

            # 10 Hz physics + publish loop
            self.timer = self.create_timer(0.1, self._physics_tick)

            self.get_logger().info('Virtual Hardware Bridge ONLINE')
            self.get_logger().info(f'Physics model: SimplifiedPhysicsModel')

        def _on_co2_valve(self, msg):
            self.physics.state.co2_valve_open = msg.data
            self.get_logger().debug(f'CO2 Valve: {"OPEN" if msg.data else "CLOSED"}')

        def _on_pump_speed(self, msg):
            self.physics.state.pump_speed_pct = msg.data
            self.get_logger().debug(f'Pump Speed: {msg.data:.1f}%')

        def _on_led_freq(self, msg):
            self.physics.state.led_pwm_freq_hz = msg.data

        def _on_led_duty(self, msg):
            self.physics.state.led_duty_pct = msg.data

        def _on_harvest_valve(self, msg):
            self.physics.state.harvest_valve_open = msg.data
            if msg.data:
                self.get_logger().info('⚠️  HARVEST VALVE OPENED')

        def _physics_tick(self):
            """Run one physics step and publish sensor readings."""
            state = self.physics.step(dt=0.1)

            # Publish sensor values
            ph_msg = Float64()
            ph_msg.data = state.ph
            self.pub_ph.publish(ph_msg)

            density_msg = Float64()
            density_msg.data = state.density_g_l
            self.pub_density.publish(density_msg)

            temp_msg = Float64()
            temp_msg.data = state.temperature_c
            self.pub_temp.publish(temp_msg)

            rpm_msg = Float64()
            rpm_msg.data = state.vortex_rpm
            self.pub_rpm.publish(rpm_msg)

            # Publish full state as JSON
            state_msg = String()
            state_msg.data = json.dumps({
                'ph': round(state.ph, 3),
                'density': round(state.density_g_l, 4),
                'temperature': round(state.temperature_c, 1),
                'rpm': round(state.vortex_rpm, 0),
                'co2_valve': state.co2_valve_open,
                'pump_pct': state.pump_speed_pct,
                'led_hz': state.led_pwm_freq_hz,
                'harvest': state.harvest_valve_open,
            })
            self.pub_state.publish(state_msg)


# ──────────────────────────────────────────────
# Standalone Mode (No ROS 2)
# ──────────────────────────────────────────────

class StandaloneSimulator:
    """
    A standalone SITL simulator for environments without ROS 2.
    Uses a simple TCP socket interface instead.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 8421):
        self.physics = SimplifiedPhysicsModel()
        self.host = host
        self.port = port
        self._running = False

    async def run(self):
        """Run the standalone simulator with a TCP command interface."""
        self._running = True
        print(f"\n  🧪 CycloTwin SITL Standalone Simulator")
        print(f"  Listening on {self.host}:{self.port}")
        print(f"  Physics: SimplifiedPhysicsModel\n")

        server = await asyncio.start_server(
            self._handle_client, self.host, self.port
        )

        # Physics loop
        physics_task = asyncio.create_task(self._physics_loop())

        async with server:
            await server.serve_forever()

    async def _physics_loop(self):
        """Continuously advance physics at 10 Hz."""
        while self._running:
            self.physics.step(dt=0.1)
            state = self.physics.state

            # Print status every 5 seconds
            if int(state._time * 10) % 50 == 0:
                print(f"  T={state._time:.0f}s | pH={state.ph:.2f} | "
                      f"D={state.density_g_l:.3f} g/L | "
                      f"T={state.temperature_c:.1f}°C | "
                      f"RPM={state.vortex_rpm:.0f}")

            await asyncio.sleep(0.1)

    async def _handle_client(self, reader, writer):
        """Handle incoming TCP commands."""
        addr = writer.get_extra_info('peername')
        print(f"  Connected: {addr}")

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                line = data.decode().strip()
                response = self._process_command(line)
                writer.write((json.dumps(response) + '\n').encode())
                await writer.drain()
        except Exception as e:
            print(f"  Client error: {e}")
        finally:
            writer.close()
            print(f"  Disconnected: {addr}")

    def _process_command(self, cmd: str) -> dict:
        """Process a single command string and return response."""
        parts = cmd.split()
        if not parts:
            return {'error': 'Empty command'}

        action = parts[0].upper()

        if action == 'GET':
            # GET — return full state
            s = self.physics.state
            return {
                'ph': round(s.ph, 3),
                'density_g_l': round(s.density_g_l, 4),
                'temperature_c': round(s.temperature_c, 1),
                'vortex_rpm': round(s.vortex_rpm, 0),
                'co2_valve': s.co2_valve_open,
                'pump_speed_pct': s.pump_speed_pct,
                'led_freq_hz': s.led_pwm_freq_hz,
                'led_duty_pct': s.led_duty_pct,
                'harvest_valve': s.harvest_valve_open,
                'time_s': round(s._time, 1),
            }

        elif action == 'SET' and len(parts) >= 3:
            # SET <param> <value>
            param = parts[1].lower()
            value = parts[2]
            s = self.physics.state

            if param == 'co2_valve':
                s.co2_valve_open = value.lower() in ('true', '1', 'on', 'open')
            elif param == 'pump_speed':
                s.pump_speed_pct = float(value)
            elif param == 'led_freq':
                s.led_pwm_freq_hz = float(value)
            elif param == 'led_duty':
                s.led_duty_pct = float(value)
            elif param == 'harvest_valve':
                s.harvest_valve_open = value.lower() in ('true', '1', 'on', 'open')
            else:
                return {'error': f'Unknown parameter: {param}'}

            return {'ok': True, 'param': param, 'value': value}

        elif action == 'RESET':
            self.physics = SimplifiedPhysicsModel()
            return {'ok': True, 'message': 'Physics reset'}

        else:
            return {'error': f'Unknown command: {cmd}'}


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

def main():
    if ROS2_AVAILABLE:
        print("ROS 2 detected — launching ROS 2 Virtual Hardware Bridge")
        rclpy.init()
        node = VirtualHardwareBridgeNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()
    else:
        print("ROS 2 not available — launching standalone TCP simulator")
        asyncio.run(StandaloneSimulator().run())


if __name__ == '__main__':
    main()
