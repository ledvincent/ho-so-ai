# DEMO-GUIDE-01 frontend contract

Artifact path: `docs/demo-guide-01-source-copy.json` (all four procedures complete).
Branch `codex/kim/demo-guide-01-source-copy`, based on reviewed combined `8c8743e`.
This is display copy only; no producer/shared API schema changes.

## Stable shape for immediate UI work

```ts
type Bilingual = { en: string; vi: string };
type Guide = {
  procedure_code: string;
  title: Bilingual;
  source: { url: string; sha256: string; retrieved_at: string;
    snapshot_id: number; parser_version: string; published_on: null; updated_on: null };
  profile: { id: number; run_id: string; baseline_id: string; output_sha256: string };
  evidence: { access: 'source_attributed'; procedure_currency: 'not_reverified';
    extraction_status: 'validated_draft'; template_approval: 'unchanged'; form_applicability: 'unresolved' };
  checklist: Array<{ id: string; kind: 'document' | 'submission_instruction';
    title: Bilingual; text: Bilingual; condition: Bilingual | null;
    originals: number | null; copies: number | null;
    source_ref: { json_pointer: string; quote_vi: string } }>;
  steps: Array<{ id: string; title: Bilingual; text: Bilingual;
    source_ref: { json_pointer: string; quote_vi: string } }>;
  conditions: Array<{ text: Bilingual;
    source_ref: { json_pointer: string; quote_vi: string } }>;
  notes: Bilingual[];
  installed_documents: Array<{ document_id: string; template_version: string;
    review_status: string; download_available: boolean }>;
};
type Artifact = { schema_version: 'display-guide.v1'; producer_commit: string;
  translation_status: 'source_attributed_working_translation';
  procedures: Record<string, Guide> };
```

Read `artifact.procedures[procedureCode]`. Bind the guide to the actual snapshot
`sha256` and, if consuming its structured profile, `profile.output_sha256`.
Do not show it as matching a changed source/version. Locale selects `.en` or `.vi`;
never use an English title followed by an unconditional Vietnamese body fallback.
Paragraph breaks in translated steps are deliberate and may render as small
paragraphs. Keep the official Vietnamese full source in an optional source view.

Show `kind: document` as checklist items with original/copy counts. Show
`submission_instruction` separately; `0/0` is the source table's instruction row,
not a document the applicant needs zero copies of. Retain conditions and all
alternatives (passport OR travel document etc.). Unknown counts stay null.
Use `installed_documents` only as a snapshot hint; the existing live discovery
action remains the authority to open a form. Three procedures have no installed
fillable workflow and still receive a useful guide; never substitute provincial
NA5 for another procedure.

## Available endpoints and translation gap

- `GET /assistant/setup`: `{procedures:[{code,name,name_en}],...}`; existing short
  English titles available. This call is read-only and makes no model request.
- `GET /procedures/{code}`: primary `source_url`, `sha256`, `fetched_at`, parser
  version, `document_json.sections[{heading,text_verbatim}]`,
  `requirements[{id,position,text_verbatim,originals,copies,...}]` and analysis.
- `GET /procedures/{code}/profile`: `{id,run_id,baseline_id,output_sha256,profile,
  sources,metadata,...}`. Structured claims retain source refs, statuses, conflicts,
  required_when and submission conditions. They are validated extraction drafts.
- `GET /procedures/{code}/documents`: installed form actions; only `1.001146`
  currently has `na5-provincial-stay-extension`, still draft/download disabled.

No dedicated English steps/checklist fields exist. Generated English aliases and
routing examples are not factual evidence. This artifact translates the captured
primary source, retains official VI and unresolved cross-source issues; it does
not establish legal currency or approve any form edition. Source retrieval is
2026-10-31, not a legal effective date. No extra model calls are used.

## Source audit and presentation handoff

Both saved-snapshot and live-GET source audits passed: four exact snapshot/profile
identities, 14 requirement rows with unchanged counts (10 document rows plus four
online-submission instructions), 12 complete steps, and 12 complete condition
clauses. Vietnamese quotes cover the full source sections without omission.
Independent content review checked alternatives, conditional photos, sponsorship
branches and the source's unresolved OR clauses. Sibling wording uses biological
sibling rather than adding an unsupported full-sibling restriction.

```powershell
python scripts/check_demo_guide.py --api-base http://127.0.0.1:8001
```

The validator only performs bounded read-only GETs for snapshots/profiles. It does
not call search, chat, embeddings, a model, or a mutation. Its success checks source
identity/coverage/counts; it is not certification of translation or legal currency.

Checklist rows reproduce the primary table. Conditional relationship evidence is
retained in the relevant family-sponsor condition; no original/copy quantity is
invented or promoted to a universal requirement. Keep conditions visible in the
guide. Step translations have paragraph breaks for readable presentation. Detailed
cross-source notes can be expandable rather than one dense default paragraph.
Do not hide an applicable condition or uncertainty when an item is selected.

The provincial fee conflict (10 USD versus no charge), differing sponsor/source
lists, online-level discrepancy, unresolved NA5 editions and separate-visa photo
count conflict remain explicit. Three procedures have no fillable workflow; guide
content remains usable without pretending an editor or official download exists.

Only this JSON, its handoff and audit script are changed. No UI, producer, shared
handler, service configuration or running process is modified. Pause after handoff.
