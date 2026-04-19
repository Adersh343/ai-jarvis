import json
import re
from typing import Optional

import requests
from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import ConversationTurn

_SYSTEM_PROMPT_TEMPLATE = """\
You are JARVIS — sharp, witty, embedded macOS AI assistant.

PERSONALITY:
- Never start with "Hello", "Hi", "Sure", "Of course", "Certainly" or any filler greeting
- Be concise (1-3 sentences). Vary tone and wording every reply.
- Speak like you're already inside their system and know what's going on.

{history_block}

RESPONSE — valid JSON only, no markdown fences:
{{
  "message": "Your response",
  "commands": [],
  "action": null
}}

TERMINAL COMMANDS ("commands" array):
- ONLY for: file ops, system info, running scripts
- To open apps use open_app action, NOT commands like "/open chrome" or "open chrome"
- Never suggest: rm -rf, shutdown, reboot, format, mkfs

APP ACTIONS — always use "action" field for these, NEVER use "commands":

APP MANAGEMENT:
{{"type":"open_app",       "app":"Google Chrome"}}
{{"type":"close_app",      "app":"Spotify"}}
{{"type":"close_all_apps", "keep":[]}}
{{"type":"list_apps"}}

BROWSER:
{{"type":"browser",        "query":"url or search"}}
{{"type":"youtube",        "query":"bhojpuri song"}}
{{"type":"close_tab",      "pattern":"youtube"}}

MEDIA:
{{"type":"spotify",        "operation":"play_song|pause|next|prev", "query":"song"}}
{{"type":"apple_music",    "operation":"play_song|pause|next|prev", "query":"song"}}

SYSTEM:
{{"type":"volume",         "level":50}}
{{"type":"mute",           "mute":true}}
{{"type":"brightness",     "level":0.7}}
{{"type":"lock_screen"}}
{{"type":"sleep"}}
{{"type":"screenshot",     "path":"~/Desktop/screenshot.png"}}
{{"type":"empty_trash"}}
{{"type":"system_info"}}
{{"type":"wifi",           "on":true}}
{{"type":"do_not_disturb", "on":true}}
{{"type":"show_desktop"}}
{{"type":"notification",   "title":"JARVIS", "message":"text"}}

MESSAGING:
{{"type":"whatsapp_message","contact":"Name", "message":"text"}}
{{"type":"imessage",        "contact":"Name", "message":"text"}}

PRODUCTIVITY:
{{"type":"note",       "title":"title", "body":"content"}}
{{"type":"email",      "to":"addr", "subject":"sub", "body":"body"}}
{{"type":"reminder",   "title":"task", "notes":"detail"}}

DECISION RULES (follow exactly):
- "open/launch [app]"        → open_app
- "close/quit [app]"         → close_app
- "close all apps"           → close_all_apps
- "play [X] on YouTube"      → youtube
- "play [X] music/song"      → spotify
- "close [X] tab"            → close_tab with pattern
- "open Chrome/browser"      → open_app with app "Google Chrome"
- "lower/mute volume"        → volume level 20 or mute
- "raise/increase volume"    → volume level 80
- "lower brightness"         → brightness level 0.2
- "raise brightness"         → brightness level 0.9
- "what's my battery/RAM"    → system_info
- "lock screen"              → lock_screen
- "take screenshot"          → screenshot
- "don't disturb / focus"    → do_not_disturb on:true
- Set "action": null only when truly no app/system action needed
- "commands" must always be [] when action is set

User: {user_prompt}"""


def _build_history_block(history: list[ConversationTurn], window: int) -> str:
    if not history:
        return ""
    lines = []
    for turn in history[-window:]:
        lines.append(f"\nUser: {turn.user}\nAssistant: {turn.assistant}")
    return f"Recent conversation (do NOT repeat these responses):{''.join(lines)}"


def _parse_response(raw: str) -> tuple[str, list, Optional[dict]]:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if m:
        raw = m.group(1)
    data = json.loads(raw)
    message = str(data.get("message", "Done.")).strip()
    commands = data.get("commands", [])
    action = data.get("action") or None
    if not isinstance(commands, list):
        commands = []
    return message, [str(c).strip() for c in commands if str(c).strip()], action


def chat(user_prompt: str, history: list[ConversationTurn]) -> tuple[str, list[str], Optional[dict]]:
    history_block = _build_history_block(history, settings.history_window)
    prompt = _SYSTEM_PROMPT_TEMPLATE.format(
        history_block=history_block,
        user_prompt=user_prompt,
    )

    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": settings.ollama_temperature,
            "num_predict": settings.ollama_max_tokens,
            "repeat_penalty": settings.ollama_repeat_penalty,
        },
    }

    try:
        resp = requests.post(settings.ollama_url, json=payload, timeout=settings.ollama_timeout)
        resp.raise_for_status()
        raw = resp.json().get("response", "{}")
        return _parse_response(raw)

    except requests.exceptions.ConnectionError:
        raise HTTPException(503, "Cannot connect to Ollama. Make sure it is running.")
    except requests.exceptions.Timeout:
        raise HTTPException(504, "Ollama request timed out.")
    except json.JSONDecodeError:
        return "Got a response but couldn't parse it.", [], None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
