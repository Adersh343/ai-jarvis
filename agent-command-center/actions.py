"""
Full macOS system control via AppleScript + shell.
"""

import subprocess
import re


def _run(script: str, timeout: int = 15) -> dict:
    r = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=timeout,
    )
    return {"ok": r.returncode == 0, "out": r.stdout.strip(), "err": r.stderr.strip()}


def _sh(cmd: str, timeout: int = 10) -> dict:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return {"ok": r.returncode == 0, "out": r.stdout.strip(), "err": r.stderr.strip()}


def _safe(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _app_running(name: str) -> bool:
    r = subprocess.run(
        ["osascript", "-e", f'tell application "System Events" to return exists process "{name}"'],
        capture_output=True, text=True
    )
    return r.stdout.strip() == "true"


def _ok(label, detail):
    return {"label": label, "status": "ok", "detail": detail}

def _fail(label, detail):
    return {"label": label, "status": "failed", "detail": detail}


# ═══════════════════════════════════════════
#  APP MANAGEMENT
# ═══════════════════════════════════════════
def open_app(app_name: str) -> dict:
    r = subprocess.run(["open", "-a", app_name], capture_output=True, text=True)
    if r.returncode == 0:
        return _ok(f"Open: {app_name}", f"Opened {app_name}")
    return _fail(f"Open: {app_name}", r.stderr.strip() or f"Could not open {app_name}")


def close_app(app_name: str) -> dict:
    name = _safe(app_name)
    r = _run(f'tell application "{name}" to quit')
    if not r["ok"]:
        # Force quit via kill if graceful quit fails
        r2 = _sh(f"pkill -x '{app_name}'")
        return _ok(f"Force quit: {app_name}", f"{app_name} closed") if r2["ok"] \
               else _fail(f"Close: {app_name}", f"{app_name} not running or couldn't close")
    return _ok(f"Close: {app_name}", f"{app_name} closed")


def close_all_apps(keep: list = None) -> dict:
    """Close all apps except Finder and optionally others in keep list."""
    always_keep = {"Finder", "SystemUIServer", "Dock", "loginwindow",
                   "Google Chrome", "Safari"}  # keep browser so UI still works
    if keep:
        always_keep.update(keep)

    script = '''
tell application "System Events"
    set appList to name of every process where background only is false
    return appList
end tell'''
    r = _run(script)
    if not r["ok"]:
        return _fail("Close all", r["err"])

    apps = [a.strip() for a in r["out"].split(",")]
    closed = []
    for app in apps:
        if app and app not in always_keep:
            _run(f'tell application "{_safe(app)}" to quit')
            closed.append(app)

    return _ok("Close all apps", f"Closed: {', '.join(closed) or 'nothing to close'}")


def list_apps() -> dict:
    script = '''
tell application "System Events"
    set appList to name of every process where background only is false
    return appList
end tell'''
    r = _run(script)
    return _ok("Running apps", r["out"]) if r["ok"] else _fail("List apps", r["err"])


# ═══════════════════════════════════════════
#  BROWSER (Chrome)
# ═══════════════════════════════════════════
def browser_open(query: str) -> dict:
    q = query.strip()
    url = q if re.match(r"^https?://", q) else \
          "https://www.google.com/search?q=" + q.replace(" ", "+")
    safe_url = _safe(url)
    script = f'''
tell application "Google Chrome"
    activate
    if (count windows) = 0 then
        make new window
        set URL of active tab of front window to "{safe_url}"
    else
        tell front window
            make new tab with properties {{URL:"{safe_url}"}}
        end tell
    end if
end tell'''
    r = _run(script)
    if not r["ok"]:
        r2 = subprocess.run(["open", safe_url], capture_output=True, text=True)
        return _ok(f"Browser: {q[:40]}", f"Opened: {url}") if r2.returncode == 0 \
               else _fail("Browser", r2.stderr)
    return _ok(f"Browser: {q[:40]}", f"Opened: {url}")


def youtube_play(query: str) -> dict:
    url = "https://www.youtube.com/results?search_query=" + query.strip().replace(" ", "+")
    return browser_open(url)


def close_tab(pattern: str = "") -> dict:
    p = _safe(pattern.lower())
    script = f'''
tell application "Google Chrome"
    set closed to 0
    repeat with w in windows
        set tabsToClose to {{}}
        repeat with t in tabs of w
            if (URL of t contains "{p}") or (title of t contains "{p}") then
                set end of tabsToClose to t
                set closed to closed + 1
            end if
        end repeat
        repeat with t in tabsToClose
            close t
        end repeat
    end repeat
    return closed
end tell''' if pattern else '''
tell application "Google Chrome"
    close active tab of front window
    return 1
end tell'''
    r = _run(script)
    return _ok(f"Close tab: {pattern or 'active'}", f"Closed {r['out']} tab(s)") if r["ok"] \
           else _fail("Close tab", r["err"])


# ═══════════════════════════════════════════
#  MEDIA
# ═══════════════════════════════════════════
def spotify(operation: str, query: str = "") -> dict:
    if not _app_running("Spotify"):
        if query:
            return youtube_play(query + " song")
        return _fail("Spotify", "Spotify not running. Try: 'play [song] on YouTube'")

    ops = {"play": "play", "pause": "pause", "play_pause": "playpause",
           "next": "next track", "prev": "previous track", "previous": "previous track"}
    if operation in ops:
        r = _run(f'tell application "Spotify" to {ops[operation]}')
        return _ok(f"Spotify: {operation}", operation) if r["ok"] else _fail("Spotify", r["err"])

    if operation in ("search", "play_song") and query:
        q = _safe(query)
        r = _run(f'''
tell application "Spotify" to activate
delay 0.5
tell application "System Events"
    keystroke "l" using command down
    delay 0.4
    keystroke "{q}"
    key code 36
end tell''')
        return _ok(f'Spotify: "{query}"', f"Playing {query}") if r["ok"] \
               else _fail("Spotify", r["err"])

    return _fail("Spotify", f"Unknown operation: {operation}")


def apple_music(operation: str, query: str = "") -> dict:
    ops = {"play": "play", "pause": "pause", "play_pause": "playpause",
           "next": "next track", "prev": "previous track"}
    if operation in ops:
        r = _run(f'tell application "Music" to {ops[operation]}')
        return _ok(f"Apple Music: {operation}", operation) if r["ok"] else _fail("Apple Music", r["err"])
    if operation in ("search", "play_song") and query:
        q = _safe(query)
        r = _run(f'tell application "Music" to activate\ntell application "Music" to search playlist "Library" for "{q}"')
        return _ok(f'Apple Music: "{query}"', f"Playing {query}") if r["ok"] \
               else youtube_play(query + " song")
    return _fail("Apple Music", f"Unknown: {operation}")


# ═══════════════════════════════════════════
#  SYSTEM CONTROLS
# ═══════════════════════════════════════════
def set_volume(level) -> dict:
    level = max(0, min(100, int(level)))
    r = _run(f"set volume output volume {level}")
    return _ok(f"Volume → {level}%", f"Volume set to {level}%") if r["ok"] \
           else _fail("Volume", r["err"])


def mute_toggle(mute: bool = True) -> dict:
    val = "true" if mute else "false"
    r = _run(f"set volume output muted {val}")
    label = "Muted" if mute else "Unmuted"
    return _ok(label, label) if r["ok"] else _fail(label, r["err"])


def set_brightness(level) -> dict:
    level = max(0.0, min(1.0, float(level)))
    pct = int(level * 100)
    try:
        r = subprocess.run(["brightness", str(level)], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return _ok(f"Brightness → {pct}%", f"Brightness set to {pct}%")
    except FileNotFoundError:
        pass
    target = max(0, int(level * 16))
    r2 = _run(f'''
tell application "System Events"
    repeat 16 times
        key code 107
        delay 0.03
    end repeat
    repeat {target} times
        key code 113
        delay 0.03
    end repeat
end tell''')
    return _ok(f"Brightness ~{pct}%", f"~{pct}% (install: brew install brightness for exact)") \
           if r2["ok"] else _fail("Brightness", "Install: brew install brightness")


def lock_screen() -> dict:
    r = _sh('pmset displaysleepnow')
    return _ok("Lock screen", "Screen locked") if r["ok"] else _fail("Lock", r["err"])


def sleep_mac() -> dict:
    r = _sh("pmset sleepnow")
    return _ok("Sleep", "Mac going to sleep") if r["ok"] else _fail("Sleep", r["err"])


def take_screenshot(path: str = "~/Desktop/screenshot.png") -> dict:
    r = _sh(f"screencapture -x {path}")
    return _ok("Screenshot", f"Saved to {path}") if r["ok"] else _fail("Screenshot", r["err"])


def empty_trash() -> dict:
    r = _sh('osascript -e \'tell application "Finder" to empty trash\'')
    return _ok("Empty Trash", "Trash emptied") if r["ok"] else _fail("Trash", r["err"])


def system_info() -> dict:
    battery = _sh("pmset -g batt | grep -o '[0-9]*%'")
    cpu     = _sh("top -l 1 -n 0 | grep 'CPU usage' | awk '{print $3}'")
    disk    = _sh("df -h / | awk 'NR==2{print $4\" free of \"$2}'")
    ram     = _sh("vm_stat | awk '/free/{free=$3} /active/{active=$3} END{printf \"%.1fGB free\", (free+active)*4096/1073741824}'")
    parts = []
    if battery["ok"] and battery["out"]: parts.append(f"Battery: {battery['out']}")
    if cpu["ok"]     and cpu["out"]:     parts.append(f"CPU: {cpu['out']}")
    if ram["ok"]     and ram["out"]:     parts.append(f"RAM: {ram['out']}")
    if disk["ok"]    and disk["out"]:    parts.append(f"Disk: {disk['out']}")
    return _ok("System info", " | ".join(parts) or "Could not fetch info")


def wifi_toggle(on: bool) -> dict:
    state = "on" if on else "off"
    r = _sh(f"networksetup -setairportpower Wi-Fi {state}")
    return _ok(f"WiFi {state}", f"WiFi turned {state}") if r["ok"] else _fail("WiFi", r["err"])


def do_not_disturb(on: bool) -> dict:
    # macOS Ventura+ uses Focus modes
    val = "true" if on else "false"
    _sh(f"defaults -currentHost write ~/Library/Preferences/ByHost/com.apple.notificationcenterui doNotDisturb -boolean {val} && killall NotificationCenter 2>/dev/null; true")
    label = f"Do Not Disturb {'on' if on else 'off'}"
    return _ok(label, label)


def show_desktop() -> dict:
    r = _run('tell application "System Events" to key code 103 using {command down, mission control key}')
    if not r["ok"]:
        r = _sh("osascript -e 'tell application \"Finder\" to set collapsed of every window to true'")
    return _ok("Show Desktop", "Desktop revealed")


def notification(title: str, message: str) -> dict:
    t, m = _safe(title), _safe(message)
    r = _run(f'display notification "{m}" with title "{t}"')
    return _ok("Notification", f"Sent: {title}") if r["ok"] else _fail("Notification", r["err"])


# ═══════════════════════════════════════════
#  MESSAGING
# ═══════════════════════════════════════════
def whatsapp_message(contact: str, message: str) -> dict:
    c, m = _safe(contact), _safe(message)
    r = _run(f'''
tell application "WhatsApp" to activate
delay 1.5
tell application "System Events"
    tell process "WhatsApp"
        keystroke "k" using command down
        delay 0.8
        keystroke "{c}"
        delay 1.8
        key code 125
        delay 0.3
        key code 36
        delay 0.8
        keystroke "{m}"
        delay 0.3
        key code 36
    end tell
end tell''')
    return {"label": f"WhatsApp → {contact}", "status": "sent" if r["ok"] else "failed",
            "detail": r["err"] or f"Message sent to {contact}"}


def imessage(contact: str, message: str) -> dict:
    c, m = _safe(contact), _safe(message)
    r = _run(f'''
tell application "Messages"
    activate
    set targetBuddy to buddy "{c}" of (first service whose service type = iMessage)
    send "{m}" to targetBuddy
end tell''')
    return {"label": f"iMessage → {contact}", "status": "sent" if r["ok"] else "failed",
            "detail": r["err"] or f"iMessage sent to {contact}"}


# ═══════════════════════════════════════════
#  NOTES / MAIL / REMINDERS
# ═══════════════════════════════════════════
def create_note(title: str, body: str = "") -> dict:
    t, b = _safe(title), _safe(body)
    r = _run(f'tell application "Notes" to activate\ntell application "Notes" to make new note with properties {{name:"{t}", body:"{b}"}}')
    return _ok(f'Note: "{title}"', f'Created "{title}"') if r["ok"] else _fail("Note", r["err"])


def compose_email(to: str, subject: str, body: str) -> dict:
    t, s, b = _safe(to), _safe(subject), _safe(body)
    r = _run(f'''
tell application "Mail"
    activate
    set msg to make new outgoing message with properties {{subject:"{s}", content:"{b}", visible:true}}
    tell msg to make new to recipient with properties {{address:"{t}"}}
end tell''')
    return _ok(f"Email to {to}", f"Draft ready") if r["ok"] else _fail("Email", r["err"])


def create_reminder(title: str, notes: str = "") -> dict:
    t, n = _safe(title), _safe(notes)
    r = _run(f'''
tell application "Reminders"
    activate
    tell list "Reminders" to make new reminder with properties {{name:"{t}", body:"{n}"}}
end tell''')
    return _ok(f'Reminder: "{title}"', f'Created "{title}"') if r["ok"] else _fail("Reminder", r["err"])


# ═══════════════════════════════════════════
#  DISPATCHER
# ═══════════════════════════════════════════
def dispatch(action: dict) -> dict:
    atype = (action or {}).get("type", "")
    try:
        return {
            # Apps
            "open_app":          lambda: open_app(action.get("app", "")),
            "close_app":         lambda: close_app(action.get("app", "")),
            "close_all_apps":    lambda: close_all_apps(action.get("keep", [])),
            "list_apps":         lambda: list_apps(),
            # Browser
            "browser":           lambda: browser_open(action.get("query", "")),
            "youtube":           lambda: youtube_play(action.get("query", "")),
            "close_tab":         lambda: close_tab(action.get("pattern", "")),
            # Media
            "spotify":           lambda: spotify(action.get("operation", "play_pause"), action.get("query", "")),
            "apple_music":       lambda: apple_music(action.get("operation", "play_pause"), action.get("query", "")),
            # System controls
            "volume":            lambda: set_volume(action.get("level", 50)),
            "mute":              lambda: mute_toggle(action.get("mute", True)),
            "brightness":        lambda: set_brightness(action.get("level", 0.5)),
            "lock_screen":       lambda: lock_screen(),
            "sleep":             lambda: sleep_mac(),
            "screenshot":        lambda: take_screenshot(action.get("path", "~/Desktop/screenshot.png")),
            "empty_trash":       lambda: empty_trash(),
            "system_info":       lambda: system_info(),
            "wifi":              lambda: wifi_toggle(action.get("on", True)),
            "do_not_disturb":    lambda: do_not_disturb(action.get("on", True)),
            "show_desktop":      lambda: show_desktop(),
            "notification":      lambda: notification(action.get("title", "JARVIS"), action.get("message", "")),
            # Messaging
            "whatsapp_message":  lambda: whatsapp_message(action.get("contact", ""), action.get("message", "")),
            "imessage":          lambda: imessage(action.get("contact", ""), action.get("message", "")),
            # Notes
            "note":              lambda: create_note(action.get("title", "Note"), action.get("body", "")),
            "email":             lambda: compose_email(action.get("to", ""), action.get("subject", ""), action.get("body", "")),
            "reminder":          lambda: create_reminder(action.get("title", ""), action.get("notes", "")),
        }.get(atype, lambda: _fail("Action", f"Unknown action: '{atype}'"))()

    except subprocess.TimeoutExpired:
        return _fail(atype, "Timed out")
    except Exception as e:
        return _fail(atype, str(e))
