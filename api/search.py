"""Retrieval only: embeddings and keyword fusion, never generated answers."""
import math
import os

import httpx
from api.config import ROOT  # Loads the project environment for compatibility.


def embedding(value):
    base = os.getenv("EMBED_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.getenv("EMBED_MODEL", "bge-m3")
    response = httpx.post(base + "/embeddings", json={"model": model, "input": value},
        headers={"Authorization": "Bearer " + os.getenv("EMBED_API_KEY", "ollama")}, timeout=60)
    response.raise_for_status()
    vector = response.json()["data"][0]["embedding"]
    if len(vector) != 1024 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vector) or not any(vector):
        raise ValueError("Expected a finite, nonzero 1024-dimensional embedding")
    return "[" + ",".join(str(v) for v in vector) + "]", model



def embed_pending():
    from api.rag_index import build, work, publish
    release = build()
    work(release)
    publish(release)
    print('Published retrieval release', release)


def search(query):
    from api.rag import search as retrieve_candidates
    return retrieve_candidates(query)
