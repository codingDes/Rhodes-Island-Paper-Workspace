from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
import re


@dataclass
class ParsedDocument:
    text: str
    text_length: int
    title_candidate: str
    preview: str


def _normalize_text(text: str) -> str:
    # Normalize whitespace so preview and length are stable.
    lines = [line.strip() for line in text.splitlines()]
    compact = "\n".join(line for line in lines if line)
    return compact.strip()


def _pick_title_candidate(text: str) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        # Skip parser page markers like [PAGE 1] / [PAGE1]
        if re.fullmatch(r"\[PAGE\s*\d+\]", candidate, flags=re.IGNORECASE):
            continue
        if len(candidate) >= 6:
            return candidate[:120]
    return "Untitled Document"


def parse_document(file_path: Path) -> ParsedDocument:
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md"}:
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
    elif suffix == ".pdf":
        try:
            doc = fitz.open(file_path)
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"Failed to open PDF: {exc}") from exc
        parts: list[str] = []
        try:
            for i, page in enumerate(doc, start=1):
                # `get_text("text")` often drops math-heavy glyph runs. Prefer sorted extraction.
                text_sorted = (page.get_text("text", sort=True) or "").strip()
                if text_sorted:
                    parts.append(f"\n\n[PAGE {i}]\n{text_sorted}")
                    continue

                # Fallback: reconstruct from dict spans (still imperfect, but keeps more symbols).
                try:
                    d = page.get_text("dict")
                except Exception:
                    d = None
                if isinstance(d, dict) and d.get("blocks"):
                    spans: list[str] = []
                    for b in d.get("blocks", []):
                        for line in b.get("lines", []) or []:
                            for span in line.get("spans", []) or []:
                                t = (span.get("text") or "").strip()
                                if t:
                                    spans.append(t)
                    if spans:
                        parts.append(f"\n\n[PAGE {i}]\n" + " ".join(spans))
                        continue

                # Last resort
                parts.append(f"\n\n[PAGE {i}]\n" + (page.get_text("text") or ""))
        finally:
            doc.close()
        raw_text = "\n".join(parts)
    else:
        raise ValueError(f"Unsupported file type for parser: {suffix or 'none'}")

    text = _normalize_text(raw_text)
    if not text:
        raise ValueError("Parsed text is empty. The file may be image-only or unreadable.")

    title_candidate = _pick_title_candidate(text)
    preview = text[:300]
    return ParsedDocument(
        text=text,
        text_length=len(text),
        title_candidate=title_candidate,
        preview=preview,
    )

