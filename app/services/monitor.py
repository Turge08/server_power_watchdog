from __future__ import annotations

import asyncio
from datetime import timedelta

from app.models import utcnow
from app.services.mqtt_service import MQTTService
from app.services.nanokvm_client import NanoKVMClient
from app.services.nut_client import NUTClient
from app.services.telegram_service import TelegramService
from app.services.usb_service import USBService
from app.state import StateStore


class MonitorService:
    def __init__(self, state: StateStore, settings_store):
        self.state = state
        self.settings_store = settings_store
        self.nut = NUTClient(self.settings_store.get)
        self.nanokvm = NanoKVMClient(self.settings_store.get)
        self.mqtt = MQTTService(self.settings_store.get)
        self.telegram = TelegramService(self.settings_store.get)
        self.usb = USBService(self.settings_store.get)

    async def initialize(self) -> None:
        now = utcnow()

        try:
            if self.mqtt.enabled():
                await self.mqtt.publish_discovery()
                self.state.add_event("info", "mqtt", "Published MQTT discovery config", now)
        except Exception as exc:
            self.state.add_event("error", "mqtt", f"MQTT discovery publish failed: {exc}", now)
            self.state.update_current(last_error=f"MQTT discovery publish failed: {exc}")

        try:
            ok = await self.nanokvm.authenticate()
            self.state.update_current(
                nanokvm_authenticated=ok,
                last_action="initial_auth",
                next_check=now + timedelta(seconds=self.settings_store.get().poll_interval),
            )
            self.state.add_event(
                "info",
                "nanokvm",
                f"Initial authentication {'succeeded' if ok else 'failed'}",
                now,
            )
        except Exception as exc:
            self.state.update_current(
                nanokvm_authenticated=False,
                last_error=str(exc),
                next_check=now + timedelta(seconds=self.settings_store.get().poll_interval),
            )
            self.state.add_event(
                "error",
                "nanokvm",
                f"Initial authentication error: {exc}",
                now,
            )

    async def run_forever(self) -> None:
        await self.initialize()

        while True:
            settings = self.settings_store.get()
            interval = max(1, int(settings.poll_interval))

            start = utcnow()
            await self.poll_once()
            end = utcnow()

            elapsed = (end - start).total_seconds()
            remaining = max(0.0, interval - elapsed)

            self.state.update_current(
                next_check=utcnow() + timedelta(seconds=remaining),
            )

            if elapsed > interval:
                self.state.add_event(
                    "warning",
                    "monitor",
                    f"Poll cycle took {elapsed:.1f}s, longer than the {interval}s poll interval",
                    utcnow(),
                )

            await asyncio.sleep(remaining)

    async def manual_power_on(self) -> bool:
        now = utcnow()
        settings = self.settings_store.get()

        if not settings.allow_power_control:
            self.state.update_current(last_action="manual_power_on_blocked")
            self.state.add_event(
                "warning",
                "safety",
                "Manual server power-on was blocked because power control is disabled",
                now,
            )
            return False

        try:
            await self.telegram.send("Server Power Watchdog is sending a manual power-on request to the server.")
        except Exception as exc:
            self.state.add_event("warning", "telegram", f"Failed to send manual power-on Telegram message: {exc}", now)

        ok = await self.nanokvm.power_on()
        self.state.update_current(
            last_power_on_attempt=now,
            last_action="manual_power_on",
        )
        self.state.add_event(
            "warning" if ok else "error",
            "nanokvm",
            "Manual server power-on request issued" if ok else "Manual server power-on request failed",
            now,
        )
        return ok

    async def poll_once(self) -> None:
        now = utcnow()
        previous = self.state.get_state().current
        settings = self.settings_store.get()

        try:
            usb_present = self.usb.is_ups_present()
            nut = self.nut.get_status()

            self.state.update_current(
                ups_usb_present=usb_present,
                nut_healthy=nut.healthy,
                ups_status=nut.status_text,
                ups_battery_percent=nut.battery_percent,
                ups_runtime_seconds=nut.runtime_seconds,
                last_check=now,
                last_error=None,
                last_action="poll",
            )

            if previous.ups_usb_present != usb_present and usb_present is not None:
                self.state.add_event(
                    "warning" if usb_present is False else "info",
                    "usb",
                    f"UPS USB {'detected' if usb_present else 'not detected'}",
                    now,
                )

            if previous.nut_healthy != nut.healthy:
                self.state.add_event(
                    "info" if nut.healthy else "error",
                    "nut",
                    f"NUT health changed to {'healthy' if nut.healthy else 'unhealthy'}",
                    now,
                )

            if previous.ups_status != nut.status_text:
                self.state.add_event(
                    "info",
                    "ups",
                    f"UPS status changed to {nut.status_text}",
                    now,
                )
                if settings.telegram_notify_ups_status_changes and self.telegram.enabled():
                    try:
                        await self.telegram.send(
                            f"UPS status changed from {previous.ups_status or 'unknown'} to {nut.status_text}."
                        )
                    except Exception as exc:
                        self.state.add_event(
                            "warning",
                            "telegram",
                            f"Failed to send UPS status Telegram message: {exc}",
                            now,
                        )

            if nut.healthy and nut.status_text in {"OL", "OL CHRG", "OL CHRG LB"}:
                power_state = await self.nanokvm.get_power_state()

                if power_state is None:
                    reauth = await self.nanokvm.authenticate()
                    self.state.update_current(nanokvm_authenticated=reauth)
                    self.state.add_event(
                        "warning",
                        "nanokvm",
                        "Power-state query required re-authentication",
                        now,
                    )
                    power_state = await self.nanokvm.get_power_state()
                else:
                    self.state.update_current(nanokvm_authenticated=True)

                if previous.server_powered_on != power_state and power_state is not None:
                    self.state.add_event(
                        "info",
                        "server",
                        f"Server power state changed to {'on' if power_state else 'off'}",
                        now,
                    )

                self.state.update_current(server_powered_on=power_state)

                if power_state is False:
                    if not settings.allow_power_control:
                        self.state.add_event(
                            "warning",
                            "safety",
                            "Server is off, but power control is disabled by configuration",
                            now,
                        )
                        return

                    current = self.state.get_state().current
                    last_attempt = current.last_power_on_attempt
                    can_attempt = (
                        last_attempt is None
                        or (now - last_attempt) >= timedelta(seconds=settings.power_on_cooldown)
                    )

                    if can_attempt:
                        if self.telegram.enabled():
                            try:
                                await self.telegram.send(
                                    "UPS is online and the server appears to be off. Server Power Watchdog is about to send a power-on request."
                                )
                            except Exception as exc:
                                self.state.add_event(
                                    "warning",
                                    "telegram",
                                    f"Failed to send pre-power-on Telegram message: {exc}",
                                    now,
                                )

                        ok = await self.nanokvm.power_on()
                        self.state.update_current(
                            last_power_on_attempt=now,
                            last_action="auto_power_on",
                        )
                        self.state.add_event(
                            "warning" if ok else "error",
                            "nanokvm",
                            "Issued automatic server power-on request" if ok else "Automatic server power-on request failed",
                            now,
                        )
                        if ok and self.telegram.enabled():
                            try:
                                await self.telegram.send("Server Power Watchdog has sent the power-on request to the server.")
                            except Exception as exc:
                                self.state.add_event(
                                    "warning",
                                    "telegram",
                                    f"Failed to send post-power-on Telegram message: {exc}",
                                    now,
                                )
            else:
                self.state.update_current(server_powered_on=None)

            try:
                mqtt_state = "online" if nut.healthy else "fault"
                await self.mqtt.publish_watchdog_status(
                    mqtt_state,
                    {
                        "ups_status": nut.status_text,
                        "nut_healthy": nut.healthy,
                        "ups_usb_present": usb_present,
                        "ups_battery_percent": nut.battery_percent,
                        "ups_runtime_seconds": nut.runtime_seconds,
                        "server_powered_on": self.state.get_state().current.server_powered_on,
                        "nanokvm_authenticated": self.state.get_state().current.nanokvm_authenticated,
                        "allow_power_control": settings.allow_power_control,
                        "last_check": self.state.get_state().current.last_check.isoformat() if self.state.get_state().current.last_check else None,
                        "last_action": self.state.get_state().current.last_action,
                        "last_error": self.state.get_state().current.last_error,
                    },
                )
            except Exception as exc:
                self.state.add_event("error", "mqtt", f"MQTT publish failed: {exc}", now)
                self.state.update_current(last_error=f"MQTT publish failed: {exc}")

        except Exception as exc:
            self.state.update_current(
                last_check=now,
                last_error=str(exc),
            )
            self.state.add_event("error", "monitor", str(exc), now)
