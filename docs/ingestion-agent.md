# Pre-analysis agent

Primary catalog: https://vpcp.dichvucong.gov.vn/p/home/dvc-trang-chu.html

## Ingest by URL

With the database, document converter and model provider configured, pass the official procedure URL directly:

```powershell
uv run python -m api.analysis "https://vpcp.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html?ma_thu_tuc=5974"
```

No `candidates.yaml` entry, procedure code, name or attachment list is needed. The agent reads the official identity, extracts the complete procedure, downloads linked forms, maps them and generates a cited profile. Successful imports become active catalog records and are exported under `data/procedures/<code>/`. Evidence and form review remain separate from ingestion.

The terminal prints the current procedure, source/form stages, model attempts and a heartbeat every 30 seconds. `Ctrl+C` records an interrupted attempt as failed. Add `--resume` to a batch to skip URLs already imported into the active catalog; omit it when refreshing sources. Failed attachments remain recorded as unavailable; they do not by themselves prevent a cited procedure profile from being imported. A `blocked` result is an imported record with review issues, while `failed` means extraction did not finish. After imports, the CLI builds, embeds and publishes app search automatically. `--no-index` defers that step. If indexing fails, imported profiles remain saved; `--resume` retries indexing without repeating those model calls. Automatic publication enables lexical routing; semantic thresholds still require calibration against the expanded catalog.

Profile extraction uses `PROFILE_MODEL` and `PROFILE_REASONING`; `.env.example` uses Sol with medium reasoning. Blank-form mapping has separate model/effort settings. API extraction allows 64,000 total output tokens (including reasoning), with one retry at 128,000 for output-limit exhaustion. Incomplete output is never accepted as a profile. Response metadata preserves status, usage and failure reason without API credentials. API rate-limit/server failures receive one bounded retry. Successful imports must then be included in a built, embedded and published retrieval release; see [RAG](rag.md).

For several procedures, pass multiple quoted URLs or create a UTF-8 text file with one URL per line:

```powershell
uv run python -m api.analysis --urls-file urls.txt
```

The researched citizen shortlist is already in `data/citizen-procedure-urls.txt`:

```powershell
uv run python -m api.analysis --urls-file data/citizen-procedure-urls.txt
```

Blank lines and `#` comments are ignored. Exact duplicate URLs are processed once. The list is validated before work starts; runtime failures are reported individually and the batch continues, exiting nonzero if any procedure fails. Saved HTML, inbox and supplementary-page overrides apply to single-URL runs only. This path does not run all-pairs catalog comparisons.

Supported national-portal hosts are `vpcp.dichvucong.gov.vn`, `dichvucong.gov.vn` and `thutuc.dichvucong.gov.vn`. The agent accepts national by-code, shared, legacy and numeric detail links. It resolves legacy/numeric links using the identity on the page, verifies the complete page's national code, and retains both the submitted URL/snapshot and resolved source in the report. Title differences between a detail card and the complete page are recorded; the extracted name and facts come from the complete page. Numeric page IDs are never stored as procedure codes. A local variant with a suffixed code is rejected pending a local-page adapter; local requirements must not be replaced silently with national requirements. Ministry of Public Security procedure links remain supported.

Forms linked from the primary page are discovered automatically. `--attachment-page` is an optional override for a supplementary supported official page, with an exact procedure-code match required. Inaccessible attachments remain explicit issues; URL-only ingestion does not invent missing files. Form version equivalence is a separate review gate.

The CLI publishes retrieval after successful imports; the library `run()` only imports one procedure. With `--no-index`, use the [retrieval workflow](rag.md) later. Neither path approves form filling or upgrades source currency automatically.

## Existing controlled reruns

`candidates.yaml` remains the selection file for the older four-procedure rerun/comparison workflow. It is not the registry for URL imports; the database holds active membership and the data index includes active exported records. The older batch and smoke-check scripts still contain four-procedure assumptions; use the URL command above for new imports.

Start at [data/README.md](../data/README.md) for the four procedure folders. Shared originals include three distinct NA5 versions and earlier exploratory forms. Current primary attachment links use explicitly labelled filename fallback; successful downloads retain their exact version. Field mappings remain draft. Procedure 1.002411 is inactive. Known stale primary procedure context is gated pending currency checks. Broken fee-detail controls remain internal provenance and do not by themselves block visible facts.

Every ingestion now also extracts the [structured procedure profile](procedure-profiles.md) under a fingerprinted baseline. Use `scripts.rerun_selected` to apply one contract to all selected procedures, compare them afterwards, and record before/after changes. Profile facts are cited; generated multilingual aliases/examples populate routing only. Missing eligibility answers remain unknown.

Run:

```powershell
docker build -f tools/documents.Dockerfile -t hoso-doc-tools .
uv run alembic upgrade head
uv run python -m scripts.rerun_selected
uv run python -m scripts.check_analysis
uv run python -m api.analysis "https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.002755" --attachment-page "https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=26345"
```

Procedure facts are extracted deterministically and preserved verbatim. A separate visual field-mapping stage sends all blank form pages, measured writable anchors, extracted text and full procedure context to GPT-6 Astra with high reasoning. Structured output identifies logical fields, owners, date components, choices, conditions, repeated areas, manual areas, evidence and uncertainties. Geometry is measured from the PDF; the model chooses anchor IDs rather than inventing coordinates. Every detected anchor must be assigned exactly once or explicitly excluded. Scanned forms and unsupported layouts need additional geometry/OCR review; detected-anchor coverage is not proof that the entire document has no other fields.

Configure `FIELD_MAPPING_PROVIDER=openai`, `OPENAI_API_KEY`, `FIELD_MAPPING_MODEL=gpt-6-astra`, and `FIELD_MAPPING_REASONING=high`. The local prototype can explicitly use `FIELD_MAPPING_PROVIDER=codex` with a signed-in CLI. The API provider uses Responses structured output, no tools and `store=false`. The CLI option uses a temporary directory, read-only sandbox and an ephemeral session. Only public blank forms and public procedure context are sent. Source contents are treated as evidence, never executable instructions. A missing key/model failure is recorded; it never silently substitutes heuristic fields as a successful model result.

Mappings are cached by original hash, rendered PDF hash, prompt/schema version and model configuration, and reused across procedures. The original context and model result are retained for audit. New revisions or renderings trigger fresh analysis. A human must still review filled examples. Summaries remain deterministic routing text; RAG enrichment is a separate task.

## Storage

- `data/procedures/<code>/`: source HTML, complete extracted procedure, internal analysis and forms.json references. No copied form binaries or field maps.
- `data/forms/_objects/<sha256>/<name>--<hash-prefix>.<actual-extension>`: the one permanent original for that fingerprint. Different bytes with the same name get different suffixes and different rows. Identical bytes fetched under another name reuse the original. Source names/URLs are preserved separately. Actual format is identified from bytes, so a .doc URL serving DOCX is stored as .docx.
- `data/forms/_objects/<sha256>/blank.pdf`, `fields.json`, `metadata.json`, `mappings/`: reusable rendering, logical fields, source/revision metadata and model evidence. Distinct previous renderings may remain under `renderings/` for audit. There are no permanent conversion input copies. The human-facing NA5 workflow, review and source files are grouped under `data/forms/NA5/`.
- `data/_store/`: HTML snapshots and run reports only for new runs. Document conversion uses temporary files that are removed afterwards.
- `data/archive/`: earlier exploration records. Known identical binaries were consolidated and references updated. `data/forms/storage-aliases.json` records their relocation.
- `attachment_observation`: append-only source URL, original filename, hash, snapshot/run, retrieval time and success/failure. A successful download is linked before conversion or model analysis. Failed processing cannot change that exact association to an inferred preferred version. Later changed bytes at the same URL produce a new observation; earlier hashes remain retained.
- `procedure_form`: the latest exact successful download for that snapshot/URL, or an explicitly labelled fallback if no successful download is known. Primary and supplementary attachment URLs are both attempted. A family preference never overwrites a direct association. `GET /forms/{sha256}/original` serves verified exact bytes with the version suffix in the filename.
- PostgreSQL `analysis_run`: run state and report, including failures.
- `procedure_analysis`: source sections, summary, quality issues and readiness.
- `form_field`: actual detected writable areas, with page, bbox, label, evidence, type, owner and requiredness. Unknown properties remain unknown. The same specification is stored in `form.fields_json`.
- `rag_chunk`: verbatim source sections and extracted form-page text with exact source URL, locator, fetch time, source snapshot and optional file hash/vector.

Blank forms and their readable exports are included in the repository. Internal HTML/run storage and inbox files are ignored by git; back up those folders alongside the database. Reports contain public source data only. Do not place completed forms or personal information in these shared folders. Use `scripts.consolidate_documents` for a plan, then `--apply` to consolidate only byte-verified duplicates; it updates references before removing any redundant file.

## RAG

Routing storage (`search_text`) contains official names and deterministic summaries. The existing hybrid search supports embeddings once configured and calibrated. Context storage (`rag_chunk`) contains steps, requirements, complete fee wording, conditions, submission methods and form instructions; generated summaries are never assistant factual context. Chunks preserve text and overlap at long boundaries. Vectors are nullable: context keyword indexes work without an embedding service; chunk-vector population is not yet implemented.

`POST /procedures/{code}/context` accepts `{"query":"..."}`. After routing selects a code, it returns the entire captured primary procedure: every visible section, all structured requirements, and each submission method with its processing time, fee and full description. No top-k or text-length cutoff silently drops procedure content. Generated summaries, source-control references and internal issue reports are excluded. It does not require form fields to be reviewed. No assistant generation endpoint or automatic submission exists.

## Review boundaries

Downloads and successful rendering establish file availability. Visible primary facts and accompanying descriptions are preserved in full; absent fee-control content is not inferred. Filename fallback is an association hypothesis, not version equivalence. Model-derived fields remain draft until the specification and fictional filled previews are reviewed. The workflow distinguishes source-requiredness from application completeness rules. Use the document's actual fonts during conversion (`FORM_FONT_DIR` or Windows font directory); a changed rendering invalidates the coordinate map and requires another pass. No ingestion or mapping command approves its own result.

## Manual downloads

Before requesting a manual download, ingestion checks the shared local form store
when an attachment download fails. A hash-verified original previously downloaded
from the exact URL can be reused with its original timestamp. Otherwise a unique
form-code match (including labels such as `Mẫu CT01 _66.doc`) is associated as a
`filename_fallback` candidate with unknown retrieval date and an explicit revision
review issue. Multiple matching versions remain unresolved. A direct download
always takes precedence. The associated local file then enters the normal mapping
and profile-extraction stages; reuse never approves a template or establishes its
current legal applicability.

Before a filename-only candidate is used, ingestion also checks
`data/forms/official-copies.json`: inspected alternate official files matched to
the exact procedure code, primary URL and label. These use `official_copy`
associations, preserve the actual alternate download URL, and retain source-bundle
hashes and page ranges for extracted PDFs. Ambiguous candidates are never assigned.
This registry is reusable offline; discovery of previously unknown official mirrors
is still a research step, not an unrestricted automatic web search.

`scripts/associate_recovered_forms.py` repairs existing missing associations without
rerunning procedure extraction. It creates new validated profile versions while
preserving existing procedure facts and citations. New form completion semantics
remain unknown pending extraction/review. `scripts/verify_form_recovery.py` checks
all hashes, profile associations/citations and exact rendering of extracted pages.

The generated [form inventory](../data/forms/index.md) lists every registered
version, a document summary, revision/review status, linked procedures, original and
known download sources. Exports refresh it; `python -m api.form_catalog` refreshes it
independently. Run database migrations before using local candidates whose original
retrieval date is unknown.

Use `data/inbox/<procedure-code>/`. Put the binary there and add `source.txt` with its original URL for human reference. Create `manifest.json` mapping the exact attachment URL to its local filename:

```json
{"https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=FILE_ID":"official-form.doc"}
```

Pass `--inbox data/inbox/<procedure-code>` to the agent. Paths must remain within that folder. Files pass the same format/render/field checks as downloads; manual supply is recorded by the invocation and source URL, but does not establish that it matches a currently inaccessible official file.
