# NA5 provincial stay-extension workflow

Open http://127.0.0.1:8000/workflows/1.001146 after starting the API. Until template approval, use fictional data only. The form supports an organisation sponsor or a family sponsor, with distinct applicant/sponsor fields. It validates required and applicable fields, dates, choices, glyph support and available printed space. It never truncates overflowing text silently.

The draft schema has 43 definitions and accounts for all 61 measured writable anchors. GPT-6 Astra with high reasoning produced the field associations from all three rendered pages. The reusable mapping includes visa and stay-extension branches; this procedure fixes the request to stay extension. Workflow completeness rules are stored separately from the model's source-requiredness findings. Print/signature/stamp areas remain manual. The official English and Vietnamese photo notes differ; the template is preserved verbatim rather than rewritten.

The original Word file remains byte-identical. The PDF was regenerated with the actual Times New Roman font after substitution caused labels and blanks to wrap incorrectly. The previous distinct rendering is retained for audit, and the model mapping was rerun against the corrected PDF geometry. The active model evidence is linked in `mapping_metadata`; all model results remain drafts.

## Verified edition and dates

- Form reference: 70/2026/TT-BCA.
- Issued: 25 May 2026; effective: 1 July 2026.
- Verified and downloaded: 31 October 2026.
- The procedure page's actual publication/update date remains unknown. It must not be filled from our download timestamp.
- Official legal metadata: https://congbao.chinhphu.vn/van-ban/thong-tu-so-70-2026-tt-bca-469801.htm
- Official attachment page: https://congan.cantho.gov.vn/thu-tuc-hanh-chinh/thutuc/gia-han-tam-tru-cho-nguoi-nuoc-ngoai-tai-viet-nam-3.html
- Download: https://congan.cantho.gov.vn/uploads/thu-tuc-hanh-chinh/na5_4.doc

The downloaded file has a .doc URL but is actually DOCX, as verified by its ZIP/XML content. Its internal text names the 2026 circular. Earlier 2015 forms remain historical; matching the name NA5 is not sufficient to override a known superseded revision. The saved national portal snapshots still cite the 2023 form. RAG context is therefore gated until those facts are checked for currency; the current form-filling workflow is separate.

## Review and release

To rerun field discovery explicitly (local signed-in CLI):

```powershell
uv run python -m scripts.map_na5 --provider codex
```

The generic procedure ingestion path uses the same mapper. Its cached map is shared across procedures. It does not run when an applicant fills in their personal details.

```powershell
uv run python -m scripts.review_na5
```

Inspect output/pdf/na5-2026-review.pdf: pages 1–3 show an organisation sponsor, pages 4–6 a foreign family sponsor. All information is fictional. Check every value, checkbox and date component, preserved notes and manual signature areas. The review packet is a raster rendering to avoid resource collisions when combining examples; actual downloads are vector PDFs.

Only after a person has reviewed the packet:

```powershell
uv run python -m scripts.review_na5 --approve-by "Reviewer name"
```

That records the review in the shared spec and database. Any field-map or template changes require a new review packet. Preview responses return a signed 15-minute token bound to the normalized values and template/spec digests. Download requires the reviewed template, that exact token and explicit user confirmation. Changes after preview invalidate the token. No applicant data is saved to files, database, browser storage or model prompts.

## Verification

```powershell
uv run pytest -q
uv run python -m scripts.check_na5_workflow
```

The HTTP smoke check uses fictional data and a temporary in-process reviewed flag to exercise final download; it never changes the persisted draft status. Production downloads remain locked until the human review command is intentionally run.
