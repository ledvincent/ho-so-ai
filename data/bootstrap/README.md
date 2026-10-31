# Tested backend data

`procedure-data.zip` is a public procedure snapshot for the shared backend. It
contains the PostgreSQL schema, data, stored embeddings and published retrieval
index, plus the source files referenced by that database. `manifest.json` records
SHA-256 hashes for the archive and every file. No UI or credentials are included.

The snapshot has exactly four procedures and 205 indexed items:

- `1.000771`: stay extension using a visa exemption certificate.
- `1.001146`: stay extension at the provincial immigration office (NA5).
- `1.003326`: stay extension at the central Immigration Department.
- `1.003342`: visa issuance at the central Immigration Department.

Newer procedures are excluded until their supporting documents and evidence
have been checked. Existing source conflicts remain visible in answers. NA5
preview is available; final download still requires human template review.

From the repository root, after starting Docker Compose:

```powershell
uv run python -m scripts.restore_backend_data --database hoso_integration
```

The command refuses to overwrite a populated database. Use a fresh database
name if needed, and set `DATABASE_URL` accordingly. It restores a PostgreSQL 16
custom-format dump through the Compose database container. No host PostgreSQL
installation is needed. Do not run migrations into the empty target before
restoring: the snapshot already includes migration `0009`.

Follow [the startup guide](../../docs/kim-start-here.md) to configure your model
key, download BGE-M3, and start the API. The model weights are downloaded
separately. The database includes vectors, so no initial reindex is needed.
