from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import requests
import os
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class PromptRequest(BaseModel):
    prompt: str

OLLAMA_URL = "http://localhost:11434/api/generate"

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(BASE_DIR, 'index.html'))

@app.get("/style.css")
async def read_css():
    return FileResponse(os.path.join(BASE_DIR, 'style.css'))

@app.get("/script.js")
async def read_js():
    return FileResponse(os.path.join(BASE_DIR, 'script.js'))

def get_assistant_response(user_prompt: str):
    system_prompt = f"""
    You are a helpful macOS Assistant. 
    Respond to the user and provide terminal commands if needed.
    
    RESPONSE FORMAT (JSON):
    {{
        "message": "Your friendly response here",
        "commands": ["command1", "command2"]
    }}
    
    RULES:
    - Always provide a "message".
    - If no commands are needed, "commands" should be [].
    - Use 'open -a "App"' for Mac apps.
    
    User Request: {user_prompt}
    """

    payload = {
        "model": "llama3.2:latest",
        "prompt": system_prompt,
        "stream": False,
        "format": "json"
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        result = response.json()
        raw = result.get('response', '{{}}')
        data = json.loads(raw)
        
        message = data.get('message', "I'm on it!")
        commands = data.get('commands', [])
        
        # Safety Filter for commands
        final_commands = []
        if isinstance(commands, list):
            for cmd in commands:
                cmd_str = str(cmd).strip()
                if cmd_str.lower() in ['safari', 'calculator', 'notes', 'chrome']:
                    final_commands.append(f"open -a {cmd_str.capitalize()}")
                else:
                    final_commands.append(cmd_str)
        
        return message, final_commands
    except:
        return "I encountered an error processing that.", []

@app.post("/execute")
async def execute_task(request: PromptRequest):
    message, commands = get_assistant_response(request.prompt)
    
    results = []
    for cmd in commands:
        try:
            process = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            results.append({
                "command": cmd,
                "stdout": process.stdout or "Done.",
                "stderr": process.stderr,
                "status": "success" if process.returncode == 0 else "error"
            })
        except Exception as e:
            results.append({"command": cmd, "error": str(e), "status": "failed"})
            
    return {"status": "completed", "message": message, "results": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
