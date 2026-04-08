from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import GlobalLorePayload, OperatorLorePayload
from app.services.chat_service import OPERATORS
from app.services import lore_service

router = APIRouter(prefix="/api", tags=["lore"])


def _payload_entries(body: OperatorLorePayload) -> list[dict]:
    return [e.model_dump() if hasattr(e, "model_dump") else e.dict() for e in body.entries]


@router.get("/lore")
def lore_index() -> dict:
    """列出共通设定与各干员设定文件概况。"""
    return lore_service.list_lore_index()


@router.get("/lore/global")
def get_global_lore() -> dict:
    """读取罗德岛/世界观共通设定（纯文本 content）。"""
    return lore_service.load_global_lore_raw()


@router.put("/lore/global")
def put_global_lore(body: GlobalLorePayload) -> dict:
    """覆盖写入共通设定。"""
    return lore_service.save_global_lore(body.content)


@router.get("/lore/operators/{operator_id}")
def get_operator_lore(operator_id: str) -> dict:
    if operator_id not in OPERATORS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未知干员 id")
    try:
        return lore_service.load_operator_lore_raw(operator_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/lore/operators/{operator_id}")
def put_operator_lore(operator_id: str, body: OperatorLorePayload) -> dict:
    if operator_id not in OPERATORS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未知干员 id")
    try:
        return lore_service.save_operator_lore(operator_id, _payload_entries(body))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
