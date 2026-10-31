# NA5 intermediary UI fixture

Read-only source: Vincent's published delivery
`9386f428e6794acd0a8b9e4cb3cc759bf5c989b4`, procedure `1.001146`,
province-level temporary stay extension for foreigners. No other catalog code
is mapped to this form. CT01 remains a separate test fixture.

## Provenance

| Local file | Producer source | SHA-256 |
| --- | --- | --- |
| `workflow.json` | `data/forms/NA5/workflow.json` | `50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3` |
| `blank.pdf` | `data/forms/_objects/a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751/blank.pdf` | `7415719c6a301bc1340b10041afd48b70ff00d4cd9ec27d0b36536128d8680af` |
| `original.docx` | Same object directory, `NA5--a17ded2807db.docx` | `a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751` |

`source.json` and `review.json` are unchanged producer manifests. The template
and mapping are awaiting human review. `schema.json` is the exact response
shape assembled by the producer's `api/workflow.py` schema route, with all 43
field definitions copied unchanged, fixed `request_type=stay_extension`, and
`review_status=draft`. JSON byte preservation is explicit in `.gitattributes`.
`example.json` is the producer's synthetic test example.

`page-1.png`, `page-2.png`, and `page-3.png` were rendered from the unchanged
blank PDF with PyMuPDF 1.28.2 at scale 1.5. `pages.json` records the original
595.303955078125 x 841.8897705078125 point page sizes. All three raster pages
were inspected. The source URL is recorded evidence, not a fresh legal check.

## UI boundary

The demo uses the exact conditional field metadata, options and placements.
It maintains one in-memory draft for deterministic field answers and manual
edits. Inactive/manual fields are excluded, sponsor changes drop inapplicable
values, and signature/certification areas remain blank. Nationality at birth
and current nationality remain distinct; no generic profile address is copied
into the temporary residential address.

The display is a local HTML overlay using Arial on the rendered blank pages.
It is not a backend-rendered PDF or a visual approval of the producer mapping.
Overflow blocks local review. Local review captures normalized current values;
any edit invalidates that snapshot and acknowledgment. Final download stays
locked: no mock review token, approval state or filled PDF is fabricated.

`transport.ts` records the exact schema/preview/download request shapes and
assistant text/citations/status/model response shape. Mock assistant output
never patches fields. No provider, profile, Clerk or workflow API is called by
this NA5 view. A real preview must later consume `application/pdf` and
`X-Review-Token`; the draft template must still be rejected for final download.
