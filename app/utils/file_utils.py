from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def sanitize_filename(name: str) -> str:
    # Keep simple and safe for local filesystem.
    unsafe = '<>:"/\\|?*'
    clean = "".join("_" if c in unsafe else c for c in name).strip()
    return clean or "uploaded_file"


def validate_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type: {suffix or 'none'}. Allowed: {allowed}")
    return suffix


def build_doc_id() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = secrets.token_hex(2)
    return f"{ts}_{rand}"

