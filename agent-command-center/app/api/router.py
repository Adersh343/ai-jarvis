from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.api.routes import chat, health
from app.services.memory import init_db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


def create_app() -> FastAPI:
    init_db()

    app = FastAPI(title="Agent Command Center", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router)

    @app.get("/")
    async def index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/style.css")
    async def css():
        return FileResponse(os.path.join(FRONTEND_DIR, "style.css"))

    @app.get("/script.js")
    async def js():
        return FileResponse(os.path.join(FRONTEND_DIR, "script.js"))

    return app
