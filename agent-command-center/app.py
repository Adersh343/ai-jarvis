from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import requests
import os
import re
import json
from typing import List, Optional

app = FastAPI(title="Agent Command Center")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class PromptRequest(BaseModel):
    prompt: str
    history: Optional[List[dict]] = []

OLLAMA_URL = "http://localhost:11434/api/generate"

BLOCKED_PATTERNS = [
    r'\brm\s+-[rRfF]{2,}\b',
    r'\brm\s+--no-preserve-root\b',
    r'\bmkfs\b',
    r'\bdd\s+if=',
    r':\(\)\{.*\}',          # fork bomb
    r'\bsudo\s+rm\b',
    r'>\s*/dev/sd',
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bhalt\b',
    r'\bpoweroff\b',
    r'(curl|wget).*\|\s*(ba)?sh',
]

def is_safe(cmd: str) -> tuple[bool, str]:
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return False, f"matches blocked pattern: {pattern}"
    return True, ""

def get_assistant_response(user_prompt: str, history: list):
    history_block = ""
    for turn in history[-6:]:
        history_block += f"\nUser: {turn.get('user', '')}\nAssistant: {turn.get('assistant', '')}"

    system_prompt = f"""You are JARVIS — a sharp, witty AI assistant built into a macOS command center.
Personality: confident, direct, occasionally dry-humored. Like Tony Stark's Jarvis — capable, not servile.

STRICT RULES FOR YOUR MESSAGE:
- NEVER start with "Hello", "Hi", "Sure", "Of course", "Certainly", "How can I", "Great question", or any filler greeting.
- Every reply must feel DIFFERENT from the last. Vary your sentence structure, tone, and wording.
- Be concise (1-3 sentences max). Get straight to the point.
- If the user greets you, respond with personality — not a generic greeting back.
- If asked something you can do with a terminal command, do it AND explain briefly.
- Speak like you actually know what's going on. You're embedded in their system.

{f'Recent conversation (do NOT repeat these responses):{history_block}' if history_block else ''}

Respond ONLY with valid JSON — no markdown, no code fences, nothing outside the JSON:
{{
    "message": "Your response here",
    "commands": ["terminal_command_if_needed"]
}}

- "commands" must be [] if no terminal action is needed
- Use 'open -a "AppName"' to open Mac apps
- Never suggest destructive commands

User said: {user_prompt}"""

    payload = {
        "model": "llama3.2:latest",
        "prompt": system_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.75,   # higher = more varied responses
            "num_predict": 512,
            "repeat_penalty": 1.2, # penalises repeating the same phrases
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=30)
        resp.raise_for_status()
        raw = resp.json().get("response", "{}")

        # Strip markdown fences if model wraps in them
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            raw = match.group(1)

        data = json.loads(raw)
        message = str(data.get("message", "Done.")).strip()
        commands = data.get("commands", [])
        if not isinstance(commands, list):
            commands = []

        safe, blocked = [], []
        for cmd in commands:
            cmd = str(cmd).strip()
            if not cmd:
                continue
            ok, reason = is_safe(cmd)
            (safe if ok else blocked).append({"command": cmd, "reason": reason} if not ok else cmd)

        return message, safe, blocked

    except requests.exceptions.ConnectionError:
        raise HTTPException(503, "Cannot connect to Ollama. Make sure it is running.")
    except requests.exceptions.Timeout:
        raise HTTPException(504, "Ollama request timed out.")
    except json.JSONDecodeError:
        return "Received a response but could not parse it.", [], []
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/health")
async def health():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        ok = r.status_code == 200
        models = [m["name"] for m in r.json().get("models", [])] if ok else []
    except Exception:
        ok, models = False, []
    return {"status": "ok", "ollama": ok, "models": models}


@app.post("/execute")
async def execute_task(request: PromptRequest):
    message, safe_cmds, blocked_cmds = get_assistant_response(
        request.prompt, request.history or []
    )

    results = []

    for item in blocked_cmds:
        results.append({
            "command": item["command"],
            "stdout": "",
            "stderr": f"Blocked: {item['reason']}",
            "status": "blocked",
        })

    for cmd in safe_cmds:
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=15, cwd=os.path.expanduser("~"),
            )
            results.append({
                "command": cmd,
                "stdout": proc.stdout.strip() or "",
                "stderr": proc.stderr.strip(),
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
            })
        except subprocess.TimeoutExpired:
            results.append({"command": cmd, "stdout": "", "stderr": "Timed out after 15s.", "status": "timeout"})
        except Exception as e:
            results.append({"command": cmd, "stdout": "", "stderr": str(e), "status": "failed"})

    return {"status": "completed", "message": message, "results": results}


@app.get("/")
async def index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/style.css")
async def css():
    return FileResponse(os.path.join(BASE_DIR, "style.css"))

@app.get("/script.js")
async def js():
    return FileResponse(os.path.join(BASE_DIR, "script.js"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
