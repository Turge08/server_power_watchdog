from __future__ import annotations

import json
from typing import Any

import paho.mqtt.publish as publish


class MQTTService:
    def __init__(self, settings_getter) -> None:
        self.settings_getter = settings_getter

    def _settings(self):
        return self.settings_getter()

    def enabled(self) -> bool:
        settings = self._settings()
        return bool(settings.mqtt_host and settings.mqtt_base_topic)

    def _auth(self):
        settings = self._settings()
        if settings.mqtt_user:
            return {
                "username": settings.mqtt_user,
                "password": settings.mqtt_password,
            }
        return None

    def _base_topic(self) -> str:
        return self._settings().mqtt_base_topic.strip().strip("/")

    async def publish_discovery(self) -> None:
        settings = self._settings()
        if not self.enabled():
            return

        base = self._base_topic()
        auth = self._auth()

        discovery_payload = {
            "name": "State",
            "state_topic": f"{base}/state",
            "json_attributes_topic": f"{base}/attributes",
            "unique_id": f"{base}_state",
            "device": {
                "name": settings.app_name,
                "identifiers": [base],
                "model": "Server Power Watchdog",
                "manufacturer": "Custom",
            },
        }

        publish.single(
            topic=f"homeassistant/sensor/{base}/config",
            payload=json.dumps(discovery_payload),
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            auth=auth,
            retain=True,
        )

    async def publish_watchdog_status(self, state: str, attributes: dict[str, Any]) -> None:
        settings = self._settings()
        if not self.enabled():
            return

        base = self._base_topic()
        auth = self._auth()

        publish.single(
            topic=f"{base}/state",
            payload=state,
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            auth=auth,
            retain=True,
        )

        publish.single(
            topic=f"{base}/attributes",
            payload=json.dumps(attributes),
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            auth=auth,
            retain=True,
        )

    async def send_test_message(self) -> None:
        settings = self._settings()
        if not self.enabled():
            raise RuntimeError("MQTT is not configured. Set MQTT host and base topic.")

        base = self._base_topic()
        auth = self._auth()

        test_payload = {
            "message": "Server Power Watchdog MQTT test message",
            "app_name": settings.app_name,
        }

        publish.single(
            topic=f"{base}/test",
            payload=json.dumps(test_payload),
            hostname=settings.mqtt_host,
            port=settings.mqtt_port,
            auth=auth,
            retain=False,
        )
