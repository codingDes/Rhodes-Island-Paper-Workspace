from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import Settings
from app.models.schemas import UploadResponse
from app.services.parser_service import parse_document
from app.services.rag_service import ensure_doc_index
from app.utils.file_utils import build_doc_id, sanitize_filename, validate_suffix

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    filename = sanitize_filename(file.filename or "uploaded_file")
    ext = Path(filename).suffix.lower()
    try:
        validate_suffix(Path(filename))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    settings = Settings.load()
    doc_id = build_doc_id()
    storage_name = f"{doc_id}{ext}"
    storage_path = Path(settings.docs_dir) / storage_name
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(content)

    try:
        parsed = parse_document(storage_path)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document parsed failed: {exc}",
        ) from exc

    parsed_text_path = Path(settings.docs_dir) / f"{doc_id}.txt"
    parsed_text_path.write_text(parsed.text, encoding="utf-8")
    # Build index ahead of time so first chat response is faster.
    ensure_doc_index(doc_id=doc_id, text=parsed.text)

    return UploadResponse(
        doc_id=doc_id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_path=str(storage_path).replace("\\", "/"),
        text_length=parsed.text_length,
        title_candidate=parsed.title_candidate,
        preview=parsed.preview,
        parsed_text_path=str(parsed_text_path).replace("\\", "/"),
    )

