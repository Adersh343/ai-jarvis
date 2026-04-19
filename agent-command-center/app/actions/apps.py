import subprocess
from ._base import run_applescript, escape, ok, fail

_SYSTEM_PROCS = {"Finder", "SystemUIServer", "Dock", "loginwindow", "Google Chrome", "Safari"}


def open_app(app_name: str) -> dict:
    r = subprocess.run(["open", "-a", app_name], capture_output=True, text=True)
    if r.returncode == 0:
        return ok(f"Open: {app_name}", f"Opened {app_name}")
    return fail(f"Open: {app_name}", r.stderr.strip() or f"Could not open {app_name}")


def close_app(app_name: str) -> dict:
    r = run_applescript(f'tell application "{escape(app_name)}" to quit')
    if not r["ok"]:
        r2 = subprocess.run(["pkill", "-x", app_name], capture_output=True, text=True)
        return ok(f"Force quit: {app_name}", f"{app_name} closed") if r2.returncode == 0 \
               else fail(f"Close: {app_name}", f"{app_name} not running or couldn't close")
    return ok(f"Close: {app_name}", f"{app_name} closed")


def close_all_apps(keep: list = None) -> dict:
    protected = _SYSTEM_PROCS | set(keep or [])
    script = '''
tell application "System Events"
    set appList to name of every process where background only is false
    return appList
end tell'''
    r = run_applescript(script)
    if not r["ok"]:
        return fail("Close all", r["err"])

    closed = []
    for app in (a.strip() for a in r["out"].split(",")):
        if app and app not in protected:
            run_applescript(f'tell application "{escape(app)}" to quit')
            closed.append(app)

    return ok("Close all apps", f"Closed: {', '.join(closed) or 'nothing to close'}")


def list_apps() -> dict:
    script = '''
tell application "System Events"
    set appList to name of every process where background only is false
    return appList
end tell'''
    r = run_applescript(script)
    return ok("Running apps", r["out"]) if r["ok"] else fail("List apps", r["err"])
