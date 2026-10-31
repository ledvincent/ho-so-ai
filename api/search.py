"""Retrieval only: embeddings and keyword fusion, never generated answers."""
import math
import os

import httpx
from sqlalchemy import text

from api.config import engine


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


def threshold():
    value = os.getenv("SEARCH_MIN_SIMILARITY")
    if value is None:
        raise RuntimeError("Search disabled: calibrate and set SEARCH_MIN_SIMILARITY first")
    number = float(value)
    if not math.isfinite(number) or not 0 < number <= 1:
        raise RuntimeError("Invalid search threshold")
    return number


def embed_pending():
    model = os.getenv("EMBED_MODEL", "bge-m3")
    with engine().connect() as db:
        rows = list(db.execute(text("""SELECT st.id,st.text FROM search_text st
            JOIN procedure p ON p.current_snapshot_id=st.snapshot_id
            WHERE st.embedding IS NULL OR st.embedding_model != :model"""), dict(model=model)).mappings())
    for row in rows:
        vector, model = embedding(row["text"])
        with engine().begin() as db:
            db.execute(text("UPDATE search_text SET embedding=CAST(:vector AS vector),embedding_model=:model WHERE id=:id"), dict(vector=vector, model=model, id=row["id"]))
    print(f"Embedded {len(rows)} search texts")


HYBRID_SQL = """
WITH eligible AS (
    SELECT st.*, p.code, s.name FROM search_text st
    JOIN procedure p ON p.current_snapshot_id=st.snapshot_id
    JOIN source_page s ON s.id=st.snapshot_id
    WHERE p.active AND s.status='parsed' AND st.embedding_model=:model AND st.embedding IS NOT NULL
    AND EXISTS (SELECT 1 FROM procedure_analysis a WHERE a.snapshot_id=s.id AND a.facts_ready)
), vector_candidates AS (
    SELECT id, code, name, 1-(embedding <=> CAST(:vector AS vector)) AS similarity,
        row_number() OVER (ORDER BY embedding <=> CAST(:vector AS vector), id) AS rank
    FROM eligible ORDER BY embedding <=> CAST(:vector AS vector), id LIMIT 50
), keyword_candidates AS (
    SELECT id, code, name,
        row_number() OVER (ORDER BY ts_rank_cd(tsv,plainto_tsquery('simple',unaccent(:query))) DESC, id) AS rank
    FROM eligible WHERE tsv @@ plainto_tsquery('simple',unaccent(:query))
    ORDER BY ts_rank_cd(tsv,plainto_tsquery('simple',unaccent(:query))) DESC, id LIMIT 50
), scores AS (
    SELECT id,code,name,1.0/(60+rank) AS score FROM vector_candidates
    UNION ALL
    SELECT id,code,name,1.0/(60+rank) AS score FROM keyword_candidates
), fused AS (
    SELECT id,code,name,sum(score) AS score FROM scores GROUP BY id,code,name
), best AS (
    SELECT DISTINCT ON (code) code,name,score FROM fused ORDER BY code,score DESC,id
), confidence AS (
    SELECT code,max(similarity) AS similarity FROM vector_candidates GROUP BY code
)
SELECT b.*,c.similarity FROM best b JOIN confidence c USING(code)
WHERE c.similarity >= :minimum ORDER BY b.score DESC,b.code LIMIT 5
"""


def search(query):
    minimum = threshold()  # Fail before making any model request if uncalibrated.
    model = os.getenv("EMBED_MODEL", "bge-m3")
    with engine().connect() as db:
        count = db.execute(text("""SELECT count(*) FROM search_text st
            JOIN procedure p ON p.current_snapshot_id=st.snapshot_id
            JOIN source_page s ON s.id=st.snapshot_id
            WHERE p.active AND s.status='parsed' AND st.embedding_model=:model AND st.embedding IS NOT NULL
            AND EXISTS (SELECT 1 FROM procedure_analysis a WHERE a.snapshot_id=s.id AND a.facts_ready)"""), dict(model=model)).scalar_one()
        if not count:
            raise RuntimeError("Search index is not ready")
        vector, model = embedding(query)
        results = [dict(r) for r in db.execute(text(HYBRID_SQL), dict(query=query, vector=vector, model=model, minimum=minimum)).mappings()]
    return dict(status="found" if results else "not_found", results=results)
