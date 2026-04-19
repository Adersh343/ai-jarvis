import subprocess
import os
from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse, CommandResult, ActionResult
from app.services import llm, memory
from app.core.security import filter_commands
from app.actions.dispatcher import dispatch
from app.core.config import settings

router = APIRouter()


def _run_command(cmd: str) -> CommandResult:
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=15, cwd=os.path.expanduser("~"),
        )
        return CommandResult(
            command=cmd,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            status="success" if proc.returncode == 0 else "error",
            returncode=proc.returncode,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(command=cmd, stdout="", stderr="Timed out after 15s.", status="timeout")
    except Exception as e:
        return CommandResult(command=cmd, stdout="", stderr=str(e), status="failed")


@router.post("/execute", response_model=ChatResponse)
async def execute(request: ChatRequest):
    db_history = memory.load(settings.history_limit)
    merged_history = db_history + (request.history or [])

    message, raw_commands, action = llm.chat(request.prompt, merged_history)

    safe_cmds, blocked_cmds = filter_commands(raw_commands)

    results: list[CommandResult] = []
    for item in blocked_cmds:
        results.append(CommandResult(
            command=item["command"], stdout="",
            stderr=f"Blocked: {item['reason']}", status="blocked",
        ))
    for cmd in safe_cmds:
        results.append(_run_command(cmd))

    action_result = None
    if action and isinstance(action, dict):
        raw = dispatch(action)
        action_result = ActionResult(**raw)

    memory.save(request.prompt, message)

    return ChatResponse(
        status="completed",
        message=message,
        results=results,
        action_result=action_result,
    )
