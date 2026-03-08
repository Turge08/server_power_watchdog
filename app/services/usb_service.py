from __future__ import annotations

import subprocess


class USBService:
    def __init__(self, settings_getter) -> None:
        self.settings_getter = settings_getter

    def is_ups_present(self) -> bool | None:
        settings = self.settings_getter()

        if not settings.usb_detection_enabled:
            return None

        usb_id = settings.ups_usb_id.strip().lower()

        try:
            proc = subprocess.run(["lsusb"], capture_output=True, text=True, check=False)
            output = proc.stdout or ""
        except FileNotFoundError:
            return None

        lowered = output.lower()

        if usb_id == "auto":
            return any(
                marker in lowered
                for marker in ["american power conversion", "apc", "uninterruptible power supply"]
            )

        if usb_id.endswith(":"):
            vendor = usb_id[:-1]
            return f"id {vendor}:" in lowered

        if ":" in usb_id:
            return f"id {usb_id}" in lowered

        return usb_id in lowered
