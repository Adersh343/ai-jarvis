import requests
from fastapi import APIRouter
from app.models.schemas import HealthResponse, HistoryResponse
from app.services import memory

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return HealthResponse(status="ok", ollama=True, models=models)
    except Exception:
        pass
    return HealthResponse(status="ok", ollama=False, models=[])


@router.get("/history", response_model=HistoryResponse)
async def get_history():
    return HistoryResponse(history=memory.load(20))


@router.delete("/history")
async def clear_history():
    memory.clear()
    return {"status": "cleared"}
