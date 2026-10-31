# Shared procedure database

`procedure-data.zip` contains the PostgreSQL schema, public procedure data,
stored embeddings and published search index. Referenced source files are either
in the archive or checked into this repository. `manifest.json` verifies both.
Credentials, applicant data, local UI and model weights are excluded.

The snapshot contains **19 active procedures: 15 citizen procedures and the four
original immigration procedures**, with **801 indexed items**, at migration `0011`.
See the [procedure catalog](../README.md) and [form index](../forms/index.md).
There are 47 recovered attachment associations across 14 citizen procedures.
The household-business form remains unresolved because its revision is ambiguous.
Form availability does not approve autofill mappings or legal applicability.
Identity-card, vehicle-registration and health-insurance facts remain gated for
source review. These review states are preserved in the database.

From the repository root, after pulling this branch:

```powershell
uv sync --locked
docker compose up -d --wait
uv run python -m scripts.restore_backend_data --database hoso_citizen_demo
```

Set `DATABASE_URL` in your local `.env` to:

```dotenv
DATABASE_URL=postgresql+psycopg://hoso:hoso_local@localhost:55432/hoso_citizen_demo
```

The command refuses to overwrite a populated database or differing source files.
For an existing installation, use a fresh database name and switch `DATABASE_URL`;
keep the previous database if you need to switch back. This is a public demo data
snapshot, not an incremental merge into an existing database. Do not run migrations
into the empty target before restoring: the schema is already included.

Follow [the startup guide](../../docs/kim-start-here.md) for model credentials,
signing secrets and API startup. No ingestion, document download or initial index
rebuild is needed. Keyword/name/code search is enabled; semantic routing has no
approved threshold for this expanded corpus and remains disabled. BGE-M3 vectors
are included for evidence retrieval; download its model separately as documented.

Maintainers: stage related source assets, then run
`uv run python -m scripts.export_backend_data`. The exporter checks the public
schema allowlist and captures a consistent PostgreSQL snapshot. Verify the archive
with `uv run python -m scripts.restore_backend_data --verify-only`, and test a fresh
restore before publishing it.
