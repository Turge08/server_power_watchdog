from __future__ import annotations

import httpx


class TelegramService:
    def __init__(self, settings_getter) -> None:
        self.settings_getter = settings_getter

    def enabled(self) -> bool:
        settings = self.settings_getter()
        return bool(settings.telegram_token and settings.telegram_chat_id)

    async def send(self, text: str) -> None:
        settings = self.settings_getter()
        if not self.enabled():
            raise RuntimeError("Telegram is not configured. Set both Telegram token and chat ID.")

        url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
        payload = {"chat_id": settings.telegram_chat_id, "text": text}

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, data=payload)

        response.raise_for_status()

    async def send_test_message(self) -> None:
        await self.send("Server Power Watchdog test message: Telegram notifications are working.")
