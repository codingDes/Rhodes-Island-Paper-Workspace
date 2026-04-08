from __future__ import annotations

from fastapi import APIRouter

from app.services.chat_service import get_operator_profiles

router = APIRouter(prefix="/api", tags=["operators"])


@router.get("/operators")
def list_operators():
    return {"items": get_operator_profiles()}

