from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np
from openai import OpenAI

from app.config import Settings


def _local_hash_embedding(text: str, dim: int) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    tokens = [t for t in text.lower().split() if t]
    if not tokens:
        return vec
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def embed_texts(texts: Iterable[str]) -> np.ndarray:
    settings = Settings.load()
    texts_list = list(texts)
    if not texts_list:
        return np.zeros((0, settings.embedding_dim), dtype=np.float32)

    try:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is empty.")
        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        resp = client.embeddings.create(model=settings.embedding_model, input=texts_list)
        arr = np.array([item.embedding for item in resp.data], dtype=np.float32)
        if arr.ndim != 2:
            raise ValueError("Invalid embedding shape from provider.")
        return arr
    except Exception:
        # Fallback local embedding keeps RAG runnable even if provider has no embedding endpoint.
        return np.array([_local_hash_embedding(t, settings.embedding_dim) for t in texts_list], dtype=np.float32)

