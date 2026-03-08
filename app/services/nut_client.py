from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class NUTStatusResult:
    healthy: bool
    status_text: str
    raw_output: str
    battery_percent: Optional[float]
    runtime_seconds: Optional[int]


class NUTClient:
    def __init__(self, settings_getter) -> None:
        self.settings_getter = settings_getter

    def _target(self) -> str:
        settings = self.settings_getter()
        return settings.nut_target_override or f"{settings.nut_ups_name}@{settings.nut_host}"

    def _clean_lines(self, text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _extract_value(self, stdout: str, stderr: str) -> str:
        stdout_lines = self._clean_lines(stdout)
        if stdout_lines:
            return stdout_lines[-1]

        stderr_lines = self._clean_lines(stderr)
        filtered = [
            line for line in stderr_lines
            if "init ssl without certificate database" not in line.lower()
        ]
        return filtered[-1] if filtered else ""

    def _run_upsc_value(self, field: str) -> tuple[int, str, str]:
        cmd = ["upsc", self._target(), field]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        value = self._extract_value(stdout, stderr)
        raw = (stdout + "\n" + stderr).strip()

        return proc.returncode, value, raw

    def _parse_float(self, value: str) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_int(self, value: str) -> Optional[int]:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def get_status(self) -> NUTStatusResult:
        status_rc, status_text, status_raw = self._run_upsc_value("ups.status")

        raw_parts = [f"ups.status={status_text}" if status_text else f"ups.status_raw={status_raw}"]
        battery_percent: Optional[float] = None
        runtime_seconds: Optional[int] = None

        if status_rc == 0:
            batt_rc, batt_value, batt_raw = self._run_upsc_value("battery.charge")
            runtime_rc, runtime_value, runtime_raw = self._run_upsc_value("battery.runtime")

            raw_parts.append(f"battery.charge={batt_value}" if batt_value else f"battery.charge_raw={batt_raw}")
            raw_parts.append(f"battery.runtime={runtime_value}" if runtime_value else f"battery.runtime_raw={runtime_raw}")

            if batt_rc == 0:
                battery_percent = self._parse_float(batt_value)

            if runtime_rc == 0:
                runtime_seconds = self._parse_int(runtime_value)

            return NUTStatusResult(
                healthy=True,
                status_text=status_text or "unknown",
                raw_output="\n".join(raw_parts),
                battery_percent=battery_percent,
                runtime_seconds=runtime_seconds,
            )

        raw_output = status_raw or status_text or "unknown"
        bad_markers = (
            "driver not connected",
            "upsd not connected",
            "not found",
            "communication",
            "connection refused",
            "data stale",
        )
        lowered = raw_output.lower()
        healthy = not any(marker in lowered for marker in bad_markers)

        return NUTStatusResult(
            healthy=healthy,
            status_text=status_text or "unknown",
            raw_output=raw_output,
            battery_percent=None,
            runtime_seconds=None,
        )
