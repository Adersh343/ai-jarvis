import re
import subprocess
from ._base import run_applescript, escape, ok, fail


def browser_open(query: str) -> dict:
    q = query.strip()
    url = q if re.match(r"^https?://", q) else \
          "https://www.google.com/search?q=" + q.replace(" ", "+")
    safe_url = escape(url)
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
    r = run_applescript(script)
    if not r["ok"]:
        r2 = subprocess.run(["open", url], capture_output=True, text=True)
        return ok(f"Browser: {q[:40]}", f"Opened: {url}") if r2.returncode == 0 \
               else fail("Browser", r2.stderr)
    return ok(f"Browser: {q[:40]}", f"Opened: {url}")


def youtube_play(query: str) -> dict:
    url = "https://www.youtube.com/results?search_query=" + query.strip().replace(" ", "+")
    return browser_open(url)


def close_tab(pattern: str = "") -> dict:
    p = escape(pattern.lower())
    if pattern:
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
end tell'''
    else:
        script = '''
tell application "Google Chrome"
    close active tab of front window
    return 1
end tell'''
    r = run_applescript(script)
    return ok(f"Close tab: {pattern or 'active'}", f"Closed {r['out']} tab(s)") if r["ok"] \
           else fail("Close tab", r["err"])
