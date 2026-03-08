from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.mqtt_service import MQTTService
from app.services.nut_manager import NUTManager
from app.services.telegram_service import TelegramService


templates = Jinja2Templates(directory="app/web/templates")
router = APIRouter()


def template_context(request: Request, extra: dict | None = None) -> dict:
    context = {
        "request": request,
        "state": request.app.state.store.get_state(),
        "settings": request.app.state.settings_store.get(),
        "settings_masked": request.app.state.settings_store.masked_dict(),
        "save_message": getattr(request.app.state, "save_message", ""),
        "nut_test_result": getattr(request.app.state, "nut_test_result", ""),
    }
    if extra:
        context.update(extra)
    return context


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", template_context(request))


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", template_context(request))


@router.post("/settings", response_class=HTMLResponse)
async def settings_save(request: Request):
    form = await request.form()
    form_data = dict(form)

    try:
        request.app.state.settings_store.update_from_form(form_data)
        request.app.state.save_message = "Settings saved."
        request.app.state.nut_test_result = ""
    except Exception as exc:
        request.app.state.save_message = f"Failed to save settings: {exc}"

    return templates.TemplateResponse("settings.html", template_context(request))


@router.post("/settings/test-telegram", response_class=HTMLResponse)
async def settings_test_telegram(request: Request):
    form = await request.form()
    request.app.state.settings_store.update_from_form(dict(form))

    telegram = TelegramService(request.app.state.settings_store.get)
    try:
        await telegram.send_test_message()
        request.app.state.save_message = "Telegram test message sent."
    except Exception as exc:
        request.app.state.save_message = f"Telegram test failed: {exc}"

    return templates.TemplateResponse("settings.html", template_context(request))


@router.post("/settings/test-mqtt", response_class=HTMLResponse)
async def settings_test_mqtt(request: Request):
    form = await request.form()
    request.app.state.settings_store.update_from_form(dict(form))

    mqtt = MQTTService(request.app.state.settings_store.get)
    try:
        await mqtt.send_test_message()
        request.app.state.save_message = "MQTT test message sent."
    except Exception as exc:
        request.app.state.save_message = f"MQTT test failed: {exc}"

    return templates.TemplateResponse("settings.html", template_context(request))


@router.post("/settings/test-nut", response_class=HTMLResponse)
async def settings_test_nut(request: Request):
    form = await request.form()
    request.app.state.settings_store.update_from_form(dict(form))

    nut_manager = NUTManager(request.app.state.settings_store.get)
    try:
        request.app.state.nut_test_result = nut_manager.test()
        request.app.state.save_message = "NUT test completed."
    except Exception as exc:
        request.app.state.save_message = f"NUT test failed: {exc}"
        request.app.state.nut_test_result = ""

    return templates.TemplateResponse("settings.html", template_context(request))


@router.get("/partials/status", response_class=HTMLResponse)
async def partial_status(request: Request):
    return templates.TemplateResponse("partials/status_cards.html", template_context(request))


@router.get("/partials/events", response_class=HTMLResponse)
async def partial_events(request: Request):
    return templates.TemplateResponse("partials/events.html", template_context(request))


@router.get("/partials/actions", response_class=HTMLResponse)
async def partial_actions(request: Request):
    return templates.TemplateResponse("partials/actions.html", template_context(request))


@router.post("/actions/power-on")
async def action_power_on(request: Request):
    await request.app.state.monitor.manual_power_on()
    return RedirectResponse(url="/partials/actions", status_code=303)
