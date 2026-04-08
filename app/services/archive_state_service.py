from __future__ import annotations

import json
import re
from pathlib import Path

from app.config import Settings
from app.models.schemas import ArchiveItem, ArchiveStateResponse

DEFAULT_CATEGORY = "未分类"
_REMOVED_CATEGORY_NAMES = {"默认分类"}


def _state_path() -> Path:
    settings = Settings.load()
    p = Path(settings.memory_dir) / "archive_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _pick_title_from_text(text: str) -> str:
    for line in text.splitlines():
        c = (line or "").strip()
        if not c:
            continue
        if re.fullmatch(r"\[PAGE\s*\d+\]", c, flags=re.IGNORECASE):
            continue
        if len(c) >= 6:
            return c[:120]
    return "Untitled Document"


def _normalize_categories(cats: list[str]) -> list[str]:
    out: list[str] = []
    for c in cats or []:
        x = str(c or "").strip()
        if not x or x in _REMOVED_CATEGORY_NAMES:
            continue
        if x not in out:
            out.append(x)
    if DEFAULT_CATEGORY not in out:
        out.insert(0, DEFAULT_CATEGORY)
    return out


def _normalize_archive_item(item: ArchiveItem, categories: list[str]) -> ArchiveItem:
    cats = [c for c in _normalize_categories(item.categories or []) if c in categories]
    if not cats:
        cats = [DEFAULT_CATEGORY]
    return ArchiveItem(
        doc_id=item.doc_id,
        filename=item.filename or f"{item.doc_id}.pdf",
        title=item.title or item.filename or item.doc_id,
        categories=cats,
        text_length=max(0, int(item.text_length or 0)),
    )


def _scan_docs_fallback() -> list[ArchiveItem]:
    settings = Settings.load()
    docs_dir = Path(settings.docs_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    out: list[ArchiveItem] = []
    for txt in sorted(docs_dir.glob("*.txt")):
        doc_id = txt.stem
        try:
            content = txt.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = ""
        title = _pick_title_from_text(content) if content else doc_id
        out.append(
            ArchiveItem(
                doc_id=doc_id,
                filename=f"{doc_id}.pdf",
                title=title,
                categories=[DEFAULT_CATEGORY],
                text_length=len(content),
            )
        )
    return out


def load_archive_state() -> ArchiveStateResponse:
    p = _state_path()
    if not p.exists():
        return ArchiveStateResponse(categories=[DEFAULT_CATEGORY], archives=_scan_docs_fallback())

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return ArchiveStateResponse(categories=[DEFAULT_CATEGORY], archives=_scan_docs_fallback())

    cats = _normalize_categories(data.get("categories", []))
    raw_archives = data.get("archives", [])
    archives: list[ArchiveItem] = []
    seen: set[str] = set()
    for raw in raw_archives:
        try:
            item = ArchiveItem(**raw)
        except Exception:
            continue
        if not item.doc_id or item.doc_id in seen:
            continue
        seen.add(item.doc_id)
        archives.append(_normalize_archive_item(item, cats))

    # Merge docs existing on disk to avoid "restart丢失"
    disk_docs = {a.doc_id: a for a in _scan_docs_fallback()}
    by_id = {a.doc_id: a for a in archives}
    for doc_id, disk_item in disk_docs.items():
        if doc_id not in by_id:
            by_id[doc_id] = disk_item
        else:
            keep = by_id[doc_id]
            if not keep.text_length and disk_item.text_length:
                keep.text_length = disk_item.text_length
            if not keep.title or re.fullmatch(r"\[PAGE\s*\d+\]", keep.title.strip(), flags=re.IGNORECASE):
                keep.title = disk_item.title
    archives = list(by_id.values())
    return ArchiveStateResponse(categories=cats, archives=archives)


def save_archive_state(categories: list[str], archives: list[ArchiveItem]) -> ArchiveStateResponse:
    cats = _normalize_categories(categories)
    normalized: list[ArchiveItem] = []
    seen: set[str] = set()
    for item in archives:
        if not item.doc_id or item.doc_id in seen:
            continue
        seen.add(item.doc_id)
        normalized.append(_normalize_archive_item(item, cats))

    payload = {
        "categories": cats,
        "archives": [a.model_dump() for a in normalized],
    }
    _state_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return load_archive_state()

