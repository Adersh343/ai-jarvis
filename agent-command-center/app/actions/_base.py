import subprocess


def run_applescript(script: str, timeout: int = 15) -> dict:
    r = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=timeout,
    )
    return {"ok": r.returncode == 0, "out": r.stdout.strip(), "err": r.stderr.strip()}


def run_shell(cmd: str, timeout: int = 10) -> dict:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return {"ok": r.returncode == 0, "out": r.stdout.strip(), "err": r.stderr.strip()}


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def app_running(name: str) -> bool:
    r = subprocess.run(
        ["osascript", "-e", f'tell application "System Events" to return exists process "{name}"'],
        capture_output=True, text=True,
    )
    return r.stdout.strip() == "true"


def ok(label: str, detail: str) -> dict:
    return {"label": label, "status": "ok", "detail": detail}


def fail(label: str, detail: str) -> dict:
    return {"label": label, "status": "failed", "detail": detail}
