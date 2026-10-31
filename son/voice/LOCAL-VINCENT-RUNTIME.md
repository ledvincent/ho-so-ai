# Local Vincent runtime — 31 October 2026

## Update: bundle restored locally

User supplied root `kim-backend-demo.zip`. Its 400-entry manifest was checked:
all listed hashes matched. Bundle source base is `9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`;
the newer runtime source remains `7c78ec4a731a2200d834f40e530eb0f2b5b9d38e` as
Vincent's installation guide instructs. Only the dump and missing `data/_store/`
and `data/archive/raw/` were copied (82 files); no newer source/form overwritten.

Actual database installation uses PostgreSQL 16.15 and upstream pgvector 0.8.1
(source tag commit `778dacf20c07caf904557a88705142631818d8cb`) **natively in WSL**.
Docker/Compose were installed first but the slow image pull was cancelled; no
Docker database/container was created. The restored cluster is `16/hoso_voice`,
loopback port 55432, new DB `hoso_kim_demo`. Existing clusters/databases were not
overwritten. Restore used `--no-owner --no-acl --exit-on-error`; runtime role hoso
has data/sequence access, with restored table ownership retained by postgres.

Observed after restoration, without any provider key or paid model call:

- Migration `0009`, four active procedures and one serving RAG index.
- Direct upstream retriever: **4/4 procedures**, four sources each, correct
  canonical code and a signed state returned (tokens not printed or stored).
- `/assistant/setup`: HTTP 200, `index_ready: true`, four procedures,
  `generation_configured: false`, model `gpt-6.1-sol`.
- `/search` for `1.001146`: HTTP 200, one matching result.
- `/assistant/chat` for a general stay-extension request: HTTP 200,
  `needs_clarification`, three choices. This is live restored retrieval, not a fixture.

BGE-M3 download has been resumed in the existing Ollama service; at handoff it
was still incomplete. Full vector routing/digest compatibility remains unverified.
Explicit codes and the observed keyword clarification work through upstream's
own supported paths; no embedding model was silently substituted or gate bypassed.

`son/voice/evals/start_vincent_private.py` now configures the restored DB and
source/model settings, validates DB availability, then requests the OpenAI key
with a masked interactive prompt. No .env is loaded, key is process-only, signed
state secrets are generated in process, and request access logging is disabled.
`son/voice/start-vincent.ps1` launches it through the isolated WSL environment.
Both scripts were syntax/path checked; the no-generation mode ran against the
restored DB. The generation path awaits the user's private key entry.

The temporary no-generation API on 8004 was stopped to free the port for that
user-owned launch. Voice gateway 8003 remains configured for 8004; old voice and
fixture servers 8000–8002 are preserved. User was asked to run the launcher and
reply once running, never paste a key into chat. Do not read the key from the
existing private voice process.

Next verification after launch: setup reports generation configured, validate
BGE-M3's exact expected digest after download, perform a bounded fictional
assistant question/clarification and voice pilot. Source readiness/form approval
remain upstream-controlled; no forms, report or personal-data integration is
established by the database restoration.

The following records describe the earlier pre-restoration state.

User explicitly requested executing Vincent's API on this machine. The exact
source snapshot `7c78ec4a731a2200d834f40e530eb0f2b5b9d38e` is extracted under
ignored `work/vincent-runtime-7c78ec4/`. No source branch merge or upstream edits.
Ubuntu 24.04 WSL already had Python and uv. `uv sync --locked --no-dev` installed
the upstream dependencies in that isolated runtime's virtual environment.

API is running on **http://127.0.0.1:8004** (WSL loopback forwarded to Windows).
The voice gateway is configured for this origin on port 8003. Existing fixture
and private voice services on ports 8000–8002 were preserved.

Observed from Windows:

- `GET /health`: 200, status ok.
- `GET /openapi.json`: 200, `/assistant/chat` present.
- `GET /assistant/setup`: 503, Database unavailable.
- `POST /assistant/chat`, fictional explicit-code question: 503, Retrieval unavailable.

The service runs with `HOSO_LOAD_DOTENV=0`, no OpenAI/assistant key inherited, no
access logging. No model call occurred. This is the real upstream API process,
but it cannot answer documentary questions until its dependencies are provisioned.

Missing prerequisites verified locally:

- No Docker executable/Desktop or PostgreSQL installation found in the checked
  Windows paths; WSL has neither docker nor psql. Ollama exists, but BGE-M3 is not
  among its installed models. Do not substitute its existing Qwen models.
- `kim-backend-demo.zip` / `procedure-db.dump` not found in Downloads, the Codex
  workspace roots or attached worktrees. Vincent's `docs/kim-start-here.md`
  explicitly requires the separate bundle for populated DB, ignored public
  evidence files and reviewed index/source identifiers. The repository alone
  does not contain the populated database. User was asked for bundle link/path.
- Assistant generation configuration must be provisioned privately after data
  restoration; no credential was read from the user's existing voice process.

Next: obtain the bundle, verify its manifest, provision a compatible PostgreSQL
16/pgvector service in isolation, restore into a new database, restore the missing
public evidence paths without overwriting newer source/form definitions, obtain
the pinned BGE-M3 model, then supply model credentials privately and verify setup.
Do not approve/reingest sources or fake review state to bypass the missing dump.

Restart API from repository root:

```powershell
wsl -d Ubuntu-24.04 -- sh -lc 'cd /mnt/c/Users/Son/Documents/Codex/ho-so-ai/work/vincent-runtime-7c78ec4 && env -u OPENAI_API_KEY -u ASSISTANT_API_KEY HOSO_LOAD_DOTENV=0 .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8004 --no-access-log'
```

This command deliberately starts the diagnostic unconfigured state. Configure
data and generation privately before expecting answers. Voice gateway command:

```powershell
son/voice/.venv/Scripts/python.exe son/voice/evals/live_rag_voice.py --assistant-url http://127.0.0.1:8004
```

Status: upstream process startup verified; actual retrieval/generation blocked.
No claim of end-to-end sourced voice compatibility. No UI, collector, producer
contract, global board or manager-owned status changed.
