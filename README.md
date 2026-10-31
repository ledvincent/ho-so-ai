# ho-so-ai

Voice-guided Vietnamese administrative procedures, with an official-source checklist
and a mobile report after the conversation. Initial recommended scope: temporary
residence registration and renewal; see `docs/scope-and-ingestion.md`.

## Team coordination

Son owns search and voice; Vincent owns official sources, structured data and
validation; Kim owns forms, the mobile report and delivery. See
[`AGENTS.md`](AGENTS.md), the [manager guide](docs/team/manager.md),
[task board](docs/team/board.md), [shared contracts](docs/team/contracts.md)
and [decisions](docs/team/decisions.md). The manager advises and prepares fixes;
humans approve merges. GitHub tests are prepared in `.github/workflows/tests.yml`
and become available after these files are published with Actions enabled.

## Capture official sources

Python 3.12+, from the repository root (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m hoso_ai.fetch
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

By default only the two `core` procedures in `coverage.json` are fetched. Use
`--code 1.004194` for one procedure, or `--include-stretch` to try the foreigner
extension. Unknown codes are rejected. No broad crawling, login or submission.

The fetcher makes sequential HTTPS GETs at least two seconds apart. It validates
titles and required sections, saves content-addressed raw files under `data/raw/`,
and records provenance and errors under `data/captures/`. Repeated bytes share a
raw file; every fetch still produces fresh retrieval metadata. Pages are fetched
again on each invocation; this is not an incremental HTTP cache.

**All output is draft.** Captured section text is a review aid, not a structured
requirements/fee API. By-code and detail pages are retained separately because
they can disagree. Legal-basis rows are references, not proof of current validity.
JavaScript-only form IDs are recorded for URL verification, never executed.
The command exits nonzero on failed downloads while retaining successful pages.
Raw captures and the local virtual environment are ignored by Git. Test fixtures
are saved public pages; tests do not use the network.
