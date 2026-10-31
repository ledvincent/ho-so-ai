# Structured procedure profiles and controlled reruns

All suggested profile fields are included. The design distinguishes sourced assertions, generated routing/question wording, and unknown/conflicting information. It does not make a procedure legally current merely by ingesting it successfully.

## Extraction contract

- Exact procedure code and official name; cited purpose, outcome and action taxonomy.
- Vietnamese/English aliases and example requests, explicitly labelled generated or sourced. These populate routing rows, never factual eligibility evidence.
- Applicant categories, structured eligibility and explicit exclusions. Conditions preserve AND/OR/NOT, supported predicates and exceptions. Missing user answers evaluate to unknown, not ineligible.
- Jurisdiction, operating authority and authority level separately. An office address does not establish a geographic eligibility restriction.
- Every submission channel, its conditions, full description, processing time and fees.
- Required documents, original/copy quantities, certification and conditional applicability.
- Procedure effective dates and supersession only when established. Form dates and retrieval timestamps cannot be substituted for procedure dates.
- Clarification criteria: reusable key, condition, generated question, cited answer options and an explicit unknown option.
- Per-procedure/per-file relationships: exact hash, code/title/aliases, revision, effective dates, required-when, completion/signing/certification roles, instructions, supporting documents, field-schema reference and registry review status.

Every factual value carries extraction status, source references and conflicts. Each reference contains a source ID, locator and supporting quote; the evidence registry resolves these to the original URL, snapshot ID, fingerprint and retrieval timestamp. Deterministic validation checks identity, source quote membership, known hashes, complete channel/document counts and well-formed conditions. A valid quote does not prove that the model interpreted it correctly: profiles remain validated drafts for review.

Schema.org's [GovernmentService](https://schema.org/GovernmentService) provides compatible concepts such as jurisdiction, operating organisation, audience, area served, channel and service output. Our profile adds explicit provenance and three-valued decision criteria.

## Catalog comparison

After all four profiles are extracted, the same configured model compares all six pairs against their original evidence. Similarity may nominate pairs in a larger catalog; it never proves a relationship. A shared NA5 file does not make procedures equivalent. Distinctions store each side's cited facts and a generated clarification question. Unsupported relationships are `not_established`.

## One baseline

```powershell
uv run alembic upgrade head
uv run python -m scripts.rerun_selected
```

The baseline pins schema/prompt fingerprints, extraction and mapping versions, model/provider/reasoning settings, criterion vocabulary, source-code fingerprints and retrieval/association policies. Manifests, exact prompts/schemas and a copy of the pinned source files are in `data/baselines/<baseline-id>/`. Changing a contract input creates a new ID.

The pipeline attempts live primary and supplementary pages and attachments. A failed page fetch can replay its recorded prior snapshot, preserving the original retrieval time and logging the failed attempt. A failed attachment fetch never overwrites an existing exact association. Stored/fallback forms pass the same mapper, with cache reuse tied to original/PDF fingerprints and mapping configuration. Successful downloads remain tied to the exact bytes presented by that URL.

Each batch records its selected codes, before/after data, semantic changes, source acquisition outcomes, validation attempts and completion/failure status under `data/runs/`. `latest.json` points to the report. An incomplete batch is explicitly labelled; individual profiles and original evidence remain available. Models receive public evidence only, not applicant personal data.

## Storage and endpoints

`analysis_baseline`, `catalog_batch`, `procedure_profile`, `procedure_profile_head` and `procedure_comparison` retain versioned results. `analysis_run.baseline_id` links ingestion to its contract. Generated search rows reference their profile ID; they are replaced when that snapshot is reanalysed, while prior profiles remain retained.

- `GET /procedures/{code}` includes the latest structured profile.
- `GET /procedures/{code}/profile` adds comparisons from a completed batch with the same baseline and exact profile run, including the namespaced evidence registry needed to resolve their citations.
- The full-procedure context endpoint keeps all original sections and adds the sourced profile; it removes generated aliases/examples. Existing source-readiness gates still apply.

`data/forms/NA5/` is the human-facing workflow/review/source folder. `data/forms/_objects/<hash>/` holds each immutable original and its distinct rendering/map versions. `storage-aliases.json` records relocations. No procedure contains copied binaries.
