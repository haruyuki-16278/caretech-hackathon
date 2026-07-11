"""POST /api/chat - テキストチャットAPI。"""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.services.conversation import process_utterance

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    result = await process_utterance(request.text, request.area)
    return ChatResponse(
        reply=result.reply,
        category=result.category,
        consult_info=result.consult_info,
        post_proposal=result.post_proposal,
    )
