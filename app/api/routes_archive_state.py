from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ArchiveStatePayload, ArchiveStateResponse
from app.services.archive_state_service import load_archive_state, save_archive_state

router = APIRouter(prefix="/api", tags=["archive-state"])


@router.get("/archive-state", response_model=ArchiveStateResponse)
def get_archive_state() -> ArchiveStateResponse:
    return load_archive_state()


@router.put("/archive-state", response_model=ArchiveStateResponse)
def put_archive_state(payload: ArchiveStatePayload) -> ArchiveStateResponse:
    return save_archive_state(payload.categories, payload.archives)

