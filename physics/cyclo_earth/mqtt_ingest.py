"""
Cyclo-Earth — MQTT Telemetry Ingestion Service
================================================

Subscribes to live MQTT telemetry from physical OpenCyclo nodes
and feeds data into the Reality Sync module.

Topics:
  opencyclo/{node_id}/status     — Full reactor state snapshot
  opencyclo/{node_id}/co2        — Cumulative CO₂ capture
  opencyclo/{node_id}/density    — Current biomass density

Spec reference: Cyclo-Earth Specification §3 Tier 3, §4
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Optional, Callable

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False


@dataclass
class MQTTConfig:
    """MQTT broker configuration."""
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "cyclo_earth_ingest"
    topic_prefix: str = "opencyclo"
    qos: int = 1


class TelemetryIngester:
    """
    MQTT subscriber that ingests live telemetry from OpenCyclo nodes.
    """

    def __init__(self, config: Optional[MQTTConfig] = None):
        self.config = config or MQTTConfig()
        self._callbacks: list[Callable] = []
        self._nodes: dict[str, dict] = {}
        self._client = None

    def on_data(self, callback: Callable):
        """Register a callback for new telemetry data."""
        self._callbacks.append(callback)

    def connect(self):
        """Connect to the MQTT broker."""
        if not MQTT_AVAILABLE:
            print("WARNING: paho-mqtt not installed. MQTT ingestion disabled.")
            print("Install with: pip install paho-mqtt")
            return False

        self._client = mqtt.Client(
            client_id=self.config.client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        if self.config.username:
            self._client.username_pw_set(self.config.username, self.config.password)

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        try:
            self._client.connect(self.config.broker_host, self.config.broker_port, 60)
            return True
        except Exception as e:
            print(f"MQTT connection failed: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Subscribe to all OpenCyclo node topics."""
        prefix = self.config.topic_prefix
        topics = [
            (f"{prefix}/+/status", self.config.qos),
            (f"{prefix}/+/co2", self.config.qos),
            (f"{prefix}/+/density", self.config.qos),
        ]
        client.subscribe(topics)
        print(f"  📡 MQTT connected. Subscribed to {prefix}/+/{{status,co2,density}}")

    def _on_message(self, client, userdata, msg):
        """Process incoming MQTT messages."""
        try:
            # Parse topic: opencyclo/{node_id}/{metric}
            parts = msg.topic.split("/")
            if len(parts) < 3:
                return

            node_id = parts[1]
            metric = parts[2]
            payload = json.loads(msg.payload.decode())

            # Update node registry
            if node_id not in self._nodes:
                self._nodes[node_id] = {
                    "node_id": node_id,
                    "first_seen": time.time(),
                    "last_seen": time.time(),
                    "metrics": {},
                }

            self._nodes[node_id]["last_seen"] = time.time()
            self._nodes[node_id]["metrics"][metric] = payload

            # Notify callbacks
            event = {
                "node_id": node_id,
                "metric": metric,
                "payload": payload,
                "timestamp": time.time(),
            }
            for cb in self._callbacks:
                try:
                    cb(event)
                except Exception as e:
                    print(f"Callback error: {e}")

        except (json.JSONDecodeError, Exception) as e:
            print(f"MQTT parse error: {e}")

    def get_active_nodes(self) -> list[dict]:
        """Return list of recently active nodes."""
        now = time.time()
        active = []
        for node_id, info in self._nodes.items():
            info["online"] = (now - info["last_seen"]) < 300  # 5min timeout
            active.append(info)
        return active

    def run_forever(self):
        """Block and process MQTT messages."""
        if self._client:
            self._client.loop_forever()


# ──────────────────────────────────────────────
# MQTT Publisher (for OpenCyclo OS nodes)
# ──────────────────────────────────────────────

class TelemetryPublisher:
    """
    Publishes reactor telemetry to the MQTT broker.
    Used by OpenCyclo OS nodes to report to Cyclo-Earth.
    """

    def __init__(self, node_id: str, config: Optional[MQTTConfig] = None):
        self.node_id = node_id
        self.config = config or MQTTConfig()
        self._client = None

    def connect(self) -> bool:
        if not MQTT_AVAILABLE:
            return False

        self._client = mqtt.Client(
            client_id=f"oc_node_{self.node_id}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        if self.config.username:
            self._client.username_pw_set(self.config.username, self.config.password)

        try:
            self._client.connect(self.config.broker_host, self.config.broker_port, 60)
            self._client.loop_start()
            return True
        except Exception as e:
            print(f"MQTT publish connection failed: {e}")
            return False

    def publish_status(self, status: dict):
        """Publish full reactor status."""
        if self._client:
            topic = f"{self.config.topic_prefix}/{self.node_id}/status"
            self._client.publish(topic, json.dumps(status), qos=self.config.qos)

    def publish_co2(self, co2_data: dict):
        """Publish CO₂ capture data."""
        if self._client:
            topic = f"{self.config.topic_prefix}/{self.node_id}/co2"
            self._client.publish(topic, json.dumps(co2_data), qos=self.config.qos)

    def publish_density(self, density: float):
        """Publish current biomass density."""
        if self._client:
            topic = f"{self.config.topic_prefix}/{self.node_id}/density"
            self._client.publish(topic, json.dumps({"density_g_l": density}), qos=self.config.qos)

    def disconnect(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()


if __name__ == "__main__":
    print("\n  📡 Cyclo-Earth MQTT Telemetry Ingester")
    print(f"  MQTT Available: {MQTT_AVAILABLE}")

    if MQTT_AVAILABLE:
        ingester = TelemetryIngester()
        ingester.on_data(lambda e: print(f"  [{e['node_id']}] {e['metric']}: {e['payload']}"))

        if ingester.connect():
            print("  Listening for telemetry...\n")
            ingester.run_forever()
        else:
            print("  Failed to connect. Is Mosquitto running?")
            print("  Start with: docker run -d -p 1883:1883 eclipse-mosquitto:2.0")
    else:
        print("  Install paho-mqtt: pip install paho-mqtt")
