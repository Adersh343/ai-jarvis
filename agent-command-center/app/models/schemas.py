from pydantic import BaseModel
from typing import Optional


class ConversationTurn(BaseModel):
    user: str
    assistant: str


class ChatRequest(BaseModel):
    prompt: str
    history: Optional[list[ConversationTurn]] = []


class CommandResult(BaseModel):
    command: str
    stdout: str
    stderr: str
    status: str
    returncode: Optional[int] = None


class ActionResult(BaseModel):
    label: str
    status: str
    detail: str


class ChatResponse(BaseModel):
    status: str
    message: str
    results: list[CommandResult]
    action_result: Optional[ActionResult] = None


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    models: list[str]


class HistoryResponse(BaseModel):
    history: list[ConversationTurn]
