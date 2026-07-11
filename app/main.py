"""FastAPI アプリケーションのエントリーポイント。"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import chat, voice

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="高齢者対話・見守り 音声チャットAPI",
    description="高齢者向けの音声入力・音声出力対応チャットページとAPI",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(chat.router)
app.include_router(voice.router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
