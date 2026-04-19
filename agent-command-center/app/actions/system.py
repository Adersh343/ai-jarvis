import subprocess
from ._base import run_applescript, run_shell, ok, fail


def set_volume(level) -> dict:
    level = max(0, min(100, int(level)))
    r = run_applescript(f"set volume output volume {level}")
    return ok(f"Volume → {level}%", f"Volume set to {level}%") if r["ok"] \
           else fail("Volume", r["err"])


def mute_toggle(mute: bool = True) -> dict:
    val = "true" if mute else "false"
    r = run_applescript(f"set volume output muted {val}")
    label = "Muted" if mute else "Unmuted"
    return ok(label, label) if r["ok"] else fail(label, r["err"])


def set_brightness(level) -> dict:
    level = max(0.0, min(1.0, float(level)))
    pct = int(level * 100)
    try:
        r = subprocess.run(["brightness", str(level)], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return ok(f"Brightness → {pct}%", f"Brightness set to {pct}%")
    except FileNotFoundError:
        pass
    target = max(0, int(level * 16))
    r2 = run_applescript(f'''
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
    return ok(f"Brightness ~{pct}%", f"~{pct}% (install: brew install brightness for exact)") \
           if r2["ok"] else fail("Brightness", "Install: brew install brightness")


def lock_screen() -> dict:
    r = run_shell("pmset displaysleepnow")
    return ok("Lock screen", "Screen locked") if r["ok"] else fail("Lock", r["err"])


def sleep_mac() -> dict:
    r = run_shell("pmset sleepnow")
    return ok("Sleep", "Mac going to sleep") if r["ok"] else fail("Sleep", r["err"])


def take_screenshot(path: str = "~/Desktop/screenshot.png") -> dict:
    r = run_shell(f"screencapture -x {path}")
    return ok("Screenshot", f"Saved to {path}") if r["ok"] else fail("Screenshot", r["err"])


def empty_trash() -> dict:
    r = run_shell('osascript -e \'tell application "Finder" to empty trash\'')
    return ok("Empty Trash", "Trash emptied") if r["ok"] else fail("Trash", r["err"])


def system_info() -> dict:
    battery = run_shell("pmset -g batt | grep -o '[0-9]*%'")
    cpu     = run_shell("top -l 1 -n 0 | grep 'CPU usage' | awk '{print $3}'")
    disk    = run_shell("df -h / | awk 'NR==2{print $4\" free of \"$2}'")
    ram     = run_shell(
        "vm_stat | awk '/free/{free=$3} /active/{active=$3} "
        "END{printf \"%.1fGB free\", (free+active)*4096/1073741824}'"
    )
    parts = []
    if battery["ok"] and battery["out"]: parts.append(f"Battery: {battery['out']}")
    if cpu["ok"]     and cpu["out"]:     parts.append(f"CPU: {cpu['out']}")
    if ram["ok"]     and ram["out"]:     parts.append(f"RAM: {ram['out']}")
    if disk["ok"]    and disk["out"]:    parts.append(f"Disk: {disk['out']}")
    return ok("System info", " | ".join(parts) or "Could not fetch info")


def wifi_toggle(on: bool) -> dict:
    state = "on" if on else "off"
    r = run_shell(f"networksetup -setairportpower Wi-Fi {state}")
    return ok(f"WiFi {state}", f"WiFi turned {state}") if r["ok"] else fail("WiFi", r["err"])


def do_not_disturb(on: bool) -> dict:
    val = "true" if on else "false"
    run_shell(
        f"defaults -currentHost write ~/Library/Preferences/ByHost/"
        f"com.apple.notificationcenterui doNotDisturb -boolean {val} "
        f"&& killall NotificationCenter 2>/dev/null; true"
    )
    label = f"Do Not Disturb {'on' if on else 'off'}"
    return ok(label, label)


def show_desktop() -> dict:
    r = run_applescript(
        'tell application "System Events" to key code 103 '
        'using {command down, mission control key}'
    )
    if not r["ok"]:
        run_shell('osascript -e \'tell application "Finder" to set collapsed of every window to true\'')
    return ok("Show Desktop", "Desktop revealed")


def send_notification(title: str, message: str) -> dict:
    from ._base import escape
    t, m = escape(title), escape(message)
    r = run_applescript(f'display notification "{m}" with title "{t}"')
    return ok("Notification", f"Sent: {title}") if r["ok"] else fail("Notification", r["err"])
