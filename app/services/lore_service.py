from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings

_ID_SAFE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")

# 注入系统提示时的总长度上限（字符），避免撑爆上下文
_MAX_GLOBAL_LORE_CHARS = 3500
_MAX_OPERATOR_LORE_CHARS = 4500


def _lore_root() -> Path:
    settings = Settings.load()
    root = Path(settings.data_dir) / "lore"
    root.mkdir(parents=True, exist_ok=True)
    (root / "operators").mkdir(parents=True, exist_ok=True)
    return root


def global_lore_path() -> Path:
    return _lore_root() / "global.json"


def operator_lore_path(operator_id: str) -> Path:
    if not _ID_SAFE.match(operator_id):
        raise ValueError("invalid operator_id")
    return _lore_root() / "operators" / f"{operator_id}.json"


def load_global_lore_raw() -> dict[str, Any]:
    path = global_lore_path()
    if not path.exists():
        return {"content": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "content" in data:
            return data
    except Exception:
        pass
    return {"content": ""}


def save_global_lore(content: str) -> dict[str, Any]:
    path = global_lore_path()
    doc = {
        "content": content or "",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def load_operator_lore_raw(operator_id: str) -> dict[str, Any]:
    path = operator_lore_path(operator_id)
    if not path.exists():
        return {"operator_id": operator_id, "entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"operator_id": operator_id, "entries": []}
        data.setdefault("operator_id", operator_id)
        data.setdefault("entries", [])
        if not isinstance(data["entries"], list):
            data["entries"] = []
        return data
    except Exception:
        return {"operator_id": operator_id, "entries": []}


def save_operator_lore(operator_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    path = operator_lore_path(operator_id)
    doc = {
        "operator_id": operator_id,
        "entries": entries,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def _format_entries(entries: list[Any], max_chars: int) -> str:
    parts: list[str] = []
    used = 0
    for item in entries:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        body = str(item.get("content") or "").strip()
        if not body and not title:
            continue
        block = ""
        if title:
            block += f"### {title}\n"
        block += body
        if used + len(block) > max_chars:
            remain = max_chars - used
            if remain > 80:
                parts.append(block[:remain].rstrip() + "…")
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts).strip()


def format_lore_for_prompt(operator_id: str) -> str:
    """拼成一段可注入 system prompt 的设定文本（罗德岛共通 + 干员私有）。"""
    chunks: list[str] = []

    g = load_global_lore_raw()
    gc = str(g.get("content") or "").strip()
    if gc:
        chunks.append(
            "【罗德岛 / 世界观共通设定（由维护者编写，非实时信息；勿与档案 PDF 混淆）】\n"
            + gc[:_MAX_GLOBAL_LORE_CHARS]
        )

    op = load_operator_lore_raw(operator_id)
    entries = op.get("entries") or []
    formatted = _format_entries(entries, _MAX_OPERATOR_LORE_CHARS)
    if formatted:
        chunks.append(
            "【本干员相关记忆与背景（由维护者编写；可引用以统一口径，勿编造未出现的事实）】\n"
            + formatted
        )

    if not chunks:
        return ""
    return "\n\n".join(chunks) + "\n\n"


def list_lore_index() -> dict[str, Any]:
    root = _lore_root()
    global_path = global_lore_path()
    global_meta = None
    if global_path.exists():
        raw = load_global_lore_raw()
        global_meta = {
            "has_content": bool(str(raw.get("content") or "").strip()),
            "updated_at": raw.get("updated_at"),
            "path": "data/lore/global.json",
        }

    op_dir = root / "operators"
    operators: list[dict[str, Any]] = []
    if op_dir.exists():
        for p in sorted(op_dir.glob("*.json")):
            oid = p.stem
            try:
                raw = load_operator_lore_raw(oid)
                n = len([e for e in (raw.get("entries") or []) if isinstance(e, dict)])
            except ValueError:
                continue
            operators.append(
                {
                    "operator_id": oid,
                    "entry_count": n,
                    "updated_at": raw.get("updated_at"),
                    "path": f"data/lore/operators/{oid}.json",
                }
            )

    return {"global": global_meta, "operators": operators}
