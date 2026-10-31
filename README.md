# Hồ Sơ AI backend

## What exists today

- A local PostgreSQL 16 database with pgvector, persisted in Docker's `hoso_pgdata` volume. Eleven migrations define the schema.
- Nineteen ingested procedures (15 citizen and four immigration), captured source evidence, shared form versions and structured profiles.
- A procedure ingestion agent with versioned prompts, schemas, model settings and recorded validation results.
- A FastAPI backend and a draft NA5 filling/preview workflow. Final form downloads remain gated on template review.
- An assistant API and versioned hybrid RAG engine with an embedding queue and signed clarification state. See [RAG setup and evaluation](docs/rag.md).

The Git repository contains code, migrations, public source/form artifacts, analysis records and a restorable public database snapshot. Follow [the shared data setup](data/bootstrap/README.md) to load the procedures and search index into a fresh database. Credentials, generated previews in `output/`, temporary files and caches stay local.

The first form workflow is at http://127.0.0.1:8000/workflows/1.001146. It uses the verified 2026 NA5; see [setup, review and release](docs/na5-workflow.md). A filled fictional review packet is under output/pdf/. Final downloads remain locked pending human template review.

Start with [the active data index](data/README.md). Each procedure folder contains source HTML, the full captured procedure, internal analysis and references to the shared forms store. Distinct form versions, PDFs and field maps live once under `data/forms/`.

Inactive exploration records have been removed from the database. Historical exploration is in `data/archive/`. The catalog contains 19 active procedures, including 15 citizen procedures; captured primary content and submission descriptions are retained. Fee-detail controls are internal provenance and do not block visible facts. Exact successful attachment downloads take precedence over inferred filename fallback. Claim-specific source conflicts are retained; reviewed procedures can supply source-attributed answers. See [scoped evidence access](docs/evidence-access.md).

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

For Kim's NA5 portal integration, start with [the handoff guide](docs/kim-start-here.md).
The checked-in [contracts](docs/contracts/README.md) describe chat responses,
document discovery and document-specific fields.

`POST /assistant/chat` connects an LLM to validated source context. See the
[assistant setup and RAG handoff contract](docs/assistant.md). Set an explicit
assistant model and API key; retrieval can be replaced independently.

To use the existing citizen procedures without running ingestion, restore the
[shared database snapshot](data/bootstrap/README.md). It includes the source files,
form associations and published search index.

## Ingestion and storage

See [the ingestion workflow](docs/ingestion-agent.md). To add a procedure, pass its government URL; its code, name and linked forms are discovered automatically. No YAML entry is required:

```powershell
uv run python -m api.analysis "https://vpcp.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html?ma_thu_tuc=5974"
# Or supply one URL per line in a UTF-8 text file:
uv run python -m api.analysis --urls-file urls.txt
```

Successful imports are stored in the active catalog and exported to `data/procedures/`. The CLI then builds and publishes app search automatically (use `--no-index` to defer it). Use `--resume` to skip successful imports and retry indexing after an interruption. Source/form review remains separate; [semantic retrieval calibration](docs/rag.md) is optional. The URL importer supports national portal links; local variants with suffixed procedure codes need a separate adapter.

`candidates.yaml` selects the existing controlled rerun/comparison batch. Build the converter and rerun that batch with:

```powershell
docker build -f tools/documents.Dockerfile -t hoso-doc-tools .
uv run python -m scripts.rerun_selected
```

The controlled batch uses one recorded baseline for all selected procedures and compares all procedure pairs afterwards. See [the profile contract](docs/procedure-profiles.md). `data/runs/latest.json` points to the batch report; each procedure has immutable before/after exports, field-level changes, evidence, model responses and validation results. PostgreSQL stores facts, profiles, versions, form relationships and cited context. Hashes identify identical content; `data/forms/_objects/` stores each original once.

`GET /procedures/1.001146` is the developer record. `GET /procedures/{code}/profile` returns the structured profile, citations and catalog distinctions. `POST /procedures/{code}/context` returns the entire captured procedure, requirements, descriptions and fees once source-currency checks pass; generated aliases/examples are excluded from factual context. Removed procedures return 404. Multilingual routing material is populated by the agent. Build, evaluate and publish the retrieval index using [the RAG workflow](docs/rag.md); source-currency review remains independent of indexing.

## Checks

```powershell
uv run pytest -q
uv run python -m scripts.check_analysis
```

The unit suite disables `.env` loading, clears inherited model keys in the test
process and blocks network access. These are test safeguards, not filesystem
access controls. The smoke check reads the local database/API and verifies all
stored file paths; run it separately with the required configuration.
