from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import AppSettings
from app.db import EventRepository
from app.services.monitor import MonitorService
from app.settings_store import SettingsStore
from app.state import StateStore
from app.web.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    defaults = AppSettings.default()
    settings_store = SettingsStore(defaults.settings_path)

    settings = settings_store.get()
    event_repo = EventRepository(settings.sqlite_path)
    store = StateStore(event_repo=event_repo, max_events=settings.max_events_in_memory)
    monitor = MonitorService(store, settings_store)

    app.state.store = store
    app.state.monitor = monitor
    app.state.settings_store = settings_store
    app.state.save_message = ""

    task = asyncio.create_task(monitor.run_forever())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Server Power Watchdog",
    debug=False,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
app.include_router(router)
