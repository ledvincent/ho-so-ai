# Hồ Sơ AI backend

For the assistant/document API handoff, start with [Kim's integration guide](docs/kim-start-here.md)
and the checked-in [OpenAPI and response examples](docs/contracts/README.md). Form schemas
are selected by document ID; NA5 is the first installed form.

## What exists today

- A local PostgreSQL 16 database with pgvector, persisted in Docker's `hoso_pgdata` volume. Nine migrations define the schema.
- Four ingested procedures, full source evidence, shared form versions, structured profiles and six catalog comparisons.
- A procedure ingestion agent with versioned prompts, schemas, model settings and recorded validation results.
- A FastAPI backend and a draft NA5 filling/preview workflow. Final form downloads remain gated on template review.
- An assistant API and versioned hybrid RAG engine with an embedding queue and signed clarification state. See [RAG setup and evaluation](docs/rag.md).

The Git repository contains code, migrations, public source/form artifacts and analysis records. It does **not** contain the running database or credentials: a fresh clone starts with an empty database after migrations. The existing local database is preserved. Generated previews in `output/`, temporary files and caches stay local.

The first form workflow is at http://127.0.0.1:8000/workflows/1.001146. It uses the verified 2026 NA5; see [setup, review and release](docs/na5-workflow.md). A filled fictional review packet is under output/pdf/. Final downloads remain locked pending human template review.

Start with [the active data index](data/README.md). Each procedure folder contains source HTML, the full captured procedure, internal analysis and references to the shared forms store. Distinct form versions, PDFs and field maps live once under `data/forms/`.

Procedure 1.002411 is inactive. Historical exploration is in `data/archive/`. The four active procedures retain all visible primary content and submission descriptions. Fee-detail controls are internal provenance and do not block visible facts. Exact successful attachment downloads take precedence over inferred filename fallback. Claim-specific source conflicts are retained; reviewed procedures can supply source-attributed answers. See [scoped evidence access](docs/evidence-access.md).

Start at [NA5](data/forms/NA5/README.md) for its workflow and revisions. The 2026 draft has 43 logical fields covering 61 measured writable areas. Older downloaded versions remain traceable in the shared object store; the same filename does not establish version equivalence.

## Run

Requires Python 3.12, uv and Docker Desktop.

```powershell
uv sync --locked
# Copy .env.example to .env if needed.
docker compose up -d --wait
uv run alembic upgrade head
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
```

API documentation: http://127.0.0.1:8000/docs

`POST /assistant/chat` connects an LLM to validated source context. See the
[assistant setup and RAG handoff contract](docs/assistant.md). Set an explicit
assistant model and API key; retrieval can be replaced independently.

## Ingestion and storage

See [the ingestion workflow](docs/ingestion-agent.md). `candidates.yaml` defines the active scope. Build the converter and rerun ingestion with:

```powershell
docker build -f tools/documents.Dockerfile -t hoso-doc-tools .
uv run python -m scripts.rerun_selected
```

The controlled batch uses one recorded baseline for all selected procedures and compares all procedure pairs afterwards. See [the profile contract](docs/procedure-profiles.md). `data/runs/latest.json` points to the batch report; each procedure has immutable before/after exports, field-level changes, evidence, model responses and validation results. PostgreSQL stores facts, profiles, versions, form relationships and cited context. Hashes identify identical content; `data/forms/_objects/` stores each original once.

`GET /procedures/1.001146` is the developer record. `GET /procedures/{code}/profile` returns the structured profile, citations and catalog distinctions. `POST /procedures/{code}/context` returns the entire captured procedure, requirements, descriptions and fees once source-currency checks pass; generated aliases/examples are excluded from factual context. Removed procedures return 404. Multilingual routing material is populated by the agent; embeddings, retrieval calibration and legal-currency review remain separate work.

## Checks

```powershell
uv run pytest -q
uv run python -m scripts.check_analysis
```

The unit suite blocks network access. The smoke check reads the local database/API and verifies all stored file paths.
