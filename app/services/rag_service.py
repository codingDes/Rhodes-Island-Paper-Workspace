from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from app.config import Settings
from app.services.chunk_service import chunk_text
from app.services.embedding_service import embed_texts


def _doc_index_paths(doc_id: str) -> tuple[Path, Path]:
    settings = Settings.load()
    idx_path = Path(settings.index_dir) / f"{doc_id}.faiss"
    meta_path = Path(settings.index_dir) / f"{doc_id}_chunks.json"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    return idx_path, meta_path


def build_doc_index(doc_id: str, text: str) -> int:
    chunks = chunk_text(text=text, chunk_size=900, overlap=150)
    if not chunks:
        raise ValueError("No chunks generated from text.")

    vectors = embed_texts(chunks).astype(np.float32)
    if vectors.shape[0] != len(chunks):
        raise ValueError("Embedding size mismatch.")

    # Cosine-like search via normalized vectors + inner product
    faiss.normalize_L2(vectors)
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    idx_path, meta_path = _doc_index_paths(doc_id)
    faiss.write_index(index, str(idx_path))
    meta_path.write_text(json.dumps({"chunks": chunks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(chunks)


def ensure_doc_index(doc_id: str, text: str) -> None:
    idx_path, meta_path = _doc_index_paths(doc_id)
    if idx_path.exists() and meta_path.exists():
        return
    build_doc_index(doc_id=doc_id, text=text)


def retrieve_chunks(doc_id: str, query: str, top_k: int = 4) -> list[str]:
    idx_path, meta_path = _doc_index_paths(doc_id)
    if not idx_path.exists() or not meta_path.exists():
        return []

    index = faiss.read_index(str(idx_path))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    chunks = meta.get("chunks", [])
    if not chunks:
        return []

    q_vec = embed_texts([query]).astype(np.float32)
    faiss.normalize_L2(q_vec)
    k = min(max(top_k, 1), len(chunks))
    _, indices = index.search(q_vec, k)
    out: list[str] = []
    for i in indices[0]:
        if 0 <= i < len(chunks):
            out.append(chunks[i])
    return out

