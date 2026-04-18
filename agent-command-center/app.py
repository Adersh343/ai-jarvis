from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess, requests, os, re, json, sqlite3
from typing import List, Optional

import actions as act

app = FastAPI(title="Agent Command Center")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "memory.db")

# ─────────────────────────────────────────
#  SQLite — persistent conversation memory
# ─────────────────────────────────────────
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL,
                ts        TEXT DEFAULT (datetime('now','localtime'))
            )
        """)
        c.commit()

init_db()

def db_save(user_msg: str, ai_msg: str):
    with sqlite3.connect(DB_PATH) as c:
        c.execute("INSERT INTO conversations (role,content) VALUES (?,?)", ("user", user_msg))
        c.execute("INSERT INTO conversations (role,content) VALUES (?,?)", ("assistant", ai_msg))
        c.commit()

def db_load(limit: int = 10) -> list:
    with sqlite3.connect(DB_PATH) as c:
        rows = c.execute(
            "SELECT role,content FROM conversations ORDER BY id DESC LIMIT ?",
            (limit * 2,)
        ).fetchall()
    rows = list(reversed(rows))
    history = []
    i = 0
    while i < len(rows) - 1:
        if rows[i][0] == "user" and rows[i+1][0] == "assistant":
            history.append({"user": rows[i][1], "assistant": rows[i+1][1]})
            i += 2
        else:
            i += 1
    return history

def db_clear():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("DELETE FROM conversations")
        c.commit()


# ─────────────────────────────────────────
#  Safety filter
# ─────────────────────────────────────────
BLOCKED = [
    r'\brm\s+-[rRfF]{2,}\b', r'\brm\s+--no-preserve-root\b',
    r'\bmkfs\b', r'\bdd\s+if=', r':\(\)\{.*\}',
    r'\bsudo\s+rm\b', r'>\s*/dev/sd',
    r'\bshutdown\b', r'\breboot\b', r'\bhalt\b', r'\bpoweroff\b',
    r'(curl|wget).*\|\s*(ba)?sh',
]
def is_safe(cmd: str):
    for p in BLOCKED:
        if re.search(p, cmd, re.IGNORECASE):
            return False, f"blocked pattern: {p}"
    return True, ""


# ─────────────────────────────────────────
#  LLM
# ─────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"

class PromptRequest(BaseModel):
    prompt:  str
    history: Optional[List[dict]] = []

def llm(user_prompt: str, history: list):
    history_block = ""
    for t in history[-6:]:
        history_block += f"\nUser: {t.get('user','')}\nAssistant: {t.get('assistant','')}"

    system_prompt = f"""You are JARVIS — sharp, witty, embedded macOS AI assistant.

PERSONALITY:
- Never start with "Hello", "Hi", "Sure", "Of course", "Certainly" or any filler greeting
- Be concise (1-3 sentences). Vary tone and wording every reply.
- Speak like you're already inside their system and know what's going on.

{f'Recent conversation (do NOT repeat these responses):{history_block}' if history_block else ''}

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
{{"type":"close_all_apps", "keep":[]}}               ← closes all except Finder/browser
{{"type":"list_apps"}}                               ← list running apps

BROWSER:
{{"type":"browser",        "query":"url or search"}} ← opens in NEW tab
{{"type":"youtube",        "query":"bhojpuri song"}} ← search YouTube in new tab
{{"type":"close_tab",      "pattern":"youtube"}}     ← close tab by URL/title match

MEDIA:
{{"type":"spotify",        "operation":"play_song|pause|next|prev", "query":"song"}}
{{"type":"apple_music",    "operation":"play_song|pause|next|prev", "query":"song"}}

SYSTEM:
{{"type":"volume",         "level":50}}              ← 0-100
{{"type":"mute",           "mute":true}}
{{"type":"brightness",     "level":0.7}}             ← 0.0 to 1.0
{{"type":"lock_screen"}}
{{"type":"sleep"}}
{{"type":"screenshot",     "path":"~/Desktop/screenshot.png"}}
{{"type":"empty_trash"}}
{{"type":"system_info"}}                             ← battery, CPU, RAM, disk
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
- "play [X] music/song"      → spotify (auto-falls back to YouTube if not installed)
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

    payload = {
        "model":  "llama3.2:latest",
        "prompt": system_prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.75, "num_predict": 512, "repeat_penalty": 1.2},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        raw = resp.json().get("response", "{}")
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if m: raw = m.group(1)
        data = json.loads(raw)

        message  = str(data.get("message", "Done.")).strip()
        commands = data.get("commands", [])
        action   = data.get("action") or None
        if not isinstance(commands, list): commands = []

        safe_cmds, blocked_cmds = [], []
        for cmd in commands:
            cmd = str(cmd).strip()
            if not cmd: continue
            ok, reason = is_safe(cmd)
            (safe_cmds if ok else blocked_cmds).append(
                cmd if ok else {"command": cmd, "reason": reason}
            )
        return message, safe_cmds, blocked_cmds, action

    except requests.exceptions.ConnectionError:
        raise HTTPException(503, "Cannot connect to Ollama. Make sure it is running.")
    except requests.exceptions.Timeout:
        raise HTTPException(504, "Ollama request timed out.")
    except json.JSONDecodeError:
        return "Got a response but couldn't parse it.", [], [], None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ─────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────
@app.get("/health")
async def health():
    try:
        r  = requests.get("http://localhost:11434/api/tags", timeout=3)
        ok = r.status_code == 200
        models = [m["name"] for m in r.json().get("models", [])] if ok else []
    except Exception:
        ok, models = False, []
    return {"status": "ok", "ollama": ok, "models": models}


@app.get("/history")
async def get_history():
    return {"history": db_load(20)}


@app.delete("/history")
async def clear_history():
    db_clear()
    return {"status": "cleared"}


@app.post("/execute")
async def execute(request: PromptRequest):
    # Merge DB history with any extra context from frontend
    db_hist = db_load(8)
    merged  = db_hist + (request.history or [])

    message, safe_cmds, blocked_cmds, action = llm(request.prompt, merged)

    results = []

    # Blocked terminal commands
    for item in blocked_cmds:
        results.append({"command": item["command"], "stdout": "", "stderr": f"Blocked: {item['reason']}", "status": "blocked"})

    # Safe terminal commands
    for cmd in safe_cmds:
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15, cwd=os.path.expanduser("~"))
            results.append({
                "command":    cmd,
                "stdout":     proc.stdout.strip() or "",
                "stderr":     proc.stderr.strip(),
                "status":     "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            results.append({"command": cmd, "stdout": "", "stderr": "Timed out after 15s.", "status": "timeout"})
        except Exception as e:
            results.append({"command": cmd, "stdout": "", "stderr": str(e), "status": "failed"})

    # App action
    action_result = None
    if action and isinstance(action, dict):
        action_result = act.dispatch(action)

    # Persist to DB
    db_save(request.prompt, message)

    return {
        "status":        "completed",
        "message":       message,
        "results":       results,
        "action_result": action_result,
    }


# Static files
@app.get("/")
async def index(): return FileResponse(os.path.join(BASE_DIR, "index.html"))
@app.get("/style.css")
async def css():   return FileResponse(os.path.join(BASE_DIR, "style.css"))
@app.get("/script.js")
async def js():    return FileResponse(os.path.join(BASE_DIR, "script.js"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
