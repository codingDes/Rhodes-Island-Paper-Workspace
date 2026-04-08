from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import (
    generate_chat_answer,
    generate_chat_answer_casual,
    generate_chat_answer_multi,
)

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/{doc_id}", response_model=ChatResponse)
def chat_document(doc_id: str, req: ChatRequest) -> ChatResponse:
    try:
        return generate_chat_answer(
            doc_id=doc_id,
            question=req.question,
            operator_id=req.operator_id,
            history=req.history,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/chat", response_model=ChatResponse)
def chat_with_focus(req: ChatRequest) -> ChatResponse:
    try:
        focus_ids = req.focus_doc_ids
        if not focus_ids:
            return generate_chat_answer_casual(
                question=req.question,
                operator_id=req.operator_id,
                history=req.history,
            )
        return generate_chat_answer_multi(
            focus_doc_ids=focus_ids,
            question=req.question,
            operator_id=req.operator_id,
            history=req.history,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

