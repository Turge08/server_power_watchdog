from __future__ import annotations

import json
import subprocess
from typing import Any, Optional
from urllib.parse import quote

import httpx


class NanoKVMClient:
    PWSECKEY = "nanokvm-sipeed-2024"

    def __init__(self, settings_getter) -> None:
        self.settings_getter = settings_getter
        self.token: Optional[str] = None

    def _settings(self):
        return self.settings_getter()

    def _base_url(self) -> str:
        settings = self._settings()
        return f"{settings.nanokvm_scheme}://{settings.nanokvm_host}"

    def _timeout(self) -> int:
        return self._settings().nanokvm_timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Cookie"] = f"nano-kvm-token={self.token}"
        return headers

    def _encrypt_password(self, password: str) -> str:
        proc = subprocess.run(
            [
                "openssl",
                "enc",
                "-aes-256-cbc",
                "-base64",
                "-salt",
                "-md",
                "md5",
                "-pass",
                f"pass:{self.PWSECKEY}",
            ],
            input=password,
            text=True,
            capture_output=True,
            check=False,
        )

        if proc.returncode != 0:
            raise RuntimeError(f"OpenSSL password encryption failed: {proc.stderr.strip()}")

        return proc.stdout.strip()

    def _build_auth_payload(self) -> str:
        settings = self._settings()
        encrypted_password = self._encrypt_password(settings.nanokvm_password)

        payload = {
            "username": quote(settings.nanokvm_username, safe=""),
            "password": quote(encrypted_password, safe=""),
        }

        return json.dumps(payload, separators=(",", ":"))

    async def authenticate(self) -> bool:
        payload = self._build_auth_payload()

        async with httpx.AsyncClient(timeout=self._timeout()) as client:
            response = await client.post(
                f"{self._base_url()}/api/auth/login",
                content=payload,
                headers={"Content-Type": "application/json"},
            )

        response.raise_for_status()

        try:
            body: Any = response.json()
        except Exception as exc:
            raise RuntimeError(
                f"NanoKVM login returned non-JSON response: {response.text[:300]}"
            ) from exc

        if not isinstance(body, dict):
            raise RuntimeError(f"NanoKVM login returned unexpected payload: {body!r}")

        data = body.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(f"NanoKVM login did not return token data. Response: {body!r}")

        token = data.get("token")
        if isinstance(token, str) and token.strip():
            self.token = token
            return True

        raise RuntimeError(f"NanoKVM login response did not include a token. Response: {body!r}")

    async def get_power_state(self) -> Optional[bool]:
        async with httpx.AsyncClient(timeout=self._timeout(), headers=self._headers()) as client:
            response = await client.get(f"{self._base_url()}/api/vm/gpio")

        if response.status_code == 401 or response.text.strip().lower() == "unauthorized":
            return None

        response.raise_for_status()

        try:
            body = response.json()
        except Exception as exc:
            raise RuntimeError(
                f"NanoKVM GPIO returned non-JSON response: {response.text[:300]}"
            ) from exc

        if not isinstance(body, dict):
            raise RuntimeError(f"NanoKVM GPIO returned unexpected payload: {body!r}")

        data = body.get("data")
        if not isinstance(data, dict):
            raise RuntimeError(f"NanoKVM GPIO did not return data object. Response: {body!r}")

        pwr = data.get("pwr")
        if pwr is None:
            return None

        return bool(pwr)

    async def power_on(self, duration_ms: int | None = None) -> bool:
        settings = self._settings()
        if not settings.allow_power_control:
            return False

        payload = {
            "type": "power",
            "duration": duration_ms or settings.nanokvm_power_duration_ms,
        }

        async with httpx.AsyncClient(timeout=self._timeout(), headers=self._headers()) as client:
            response = await client.post(f"{self._base_url()}/api/vm/gpio", json=payload)

        if response.status_code == 401 or response.text.strip().lower() == "unauthorized":
            return False

        response.raise_for_status()
        return True
