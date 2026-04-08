from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import SummaryResponse
from app.services.summary_service import generate_structured_summary

router = APIRouter(prefix="/api", tags=["summary"])


@router.post("/summary/{doc_id}", response_model=SummaryResponse)
def summary_document(doc_id: str) -> SummaryResponse:
    try:
        return generate_structured_summary(doc_id=doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

