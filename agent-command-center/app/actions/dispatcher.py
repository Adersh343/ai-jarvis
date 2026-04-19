import subprocess
from ._base import fail
from . import apps, browser, media, system, messaging


_ACTION_MAP = {
    "open_app":         lambda a: apps.open_app(a.get("app", "")),
    "close_app":        lambda a: apps.close_app(a.get("app", "")),
    "close_all_apps":   lambda a: apps.close_all_apps(a.get("keep", [])),
    "list_apps":        lambda a: apps.list_apps(),

    "browser":          lambda a: browser.browser_open(a.get("query", "")),
    "youtube":          lambda a: browser.youtube_play(a.get("query", "")),
    "close_tab":        lambda a: browser.close_tab(a.get("pattern", "")),

    "spotify":          lambda a: media.spotify(a.get("operation", "play_pause"), a.get("query", "")),
    "apple_music":      lambda a: media.apple_music(a.get("operation", "play_pause"), a.get("query", "")),

    "volume":           lambda a: system.set_volume(a.get("level", 50)),
    "mute":             lambda a: system.mute_toggle(a.get("mute", True)),
    "brightness":       lambda a: system.set_brightness(a.get("level", 0.5)),
    "lock_screen":      lambda a: system.lock_screen(),
    "sleep":            lambda a: system.sleep_mac(),
    "screenshot":       lambda a: system.take_screenshot(a.get("path", "~/Desktop/screenshot.png")),
    "empty_trash":      lambda a: system.empty_trash(),
    "system_info":      lambda a: system.system_info(),
    "wifi":             lambda a: system.wifi_toggle(a.get("on", True)),
    "do_not_disturb":   lambda a: system.do_not_disturb(a.get("on", True)),
    "show_desktop":     lambda a: system.show_desktop(),
    "notification":     lambda a: system.send_notification(a.get("title", "JARVIS"), a.get("message", "")),

    "whatsapp_message": lambda a: messaging.whatsapp_message(a.get("contact", ""), a.get("message", "")),
    "imessage":         lambda a: messaging.imessage(a.get("contact", ""), a.get("message", "")),
    "note":             lambda a: messaging.create_note(a.get("title", "Note"), a.get("body", "")),
    "email":            lambda a: messaging.compose_email(a.get("to", ""), a.get("subject", ""), a.get("body", "")),
    "reminder":         lambda a: messaging.create_reminder(a.get("title", ""), a.get("notes", "")),
}


def dispatch(action: dict) -> dict:
    if not action or not isinstance(action, dict):
        return fail("Action", "Invalid action payload")
    atype = action.get("type", "")
    handler = _ACTION_MAP.get(atype)
    if not handler:
        return fail("Action", f"Unknown action: '{atype}'")
    try:
        return handler(action)
    except subprocess.TimeoutExpired:
        return fail(atype, "Timed out")
    except Exception as e:
        return fail(atype, str(e))
