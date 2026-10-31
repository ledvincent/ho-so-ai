# Local Vincent runtime — 31 October 2026

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
