# Form rendering: synthetic seam, not official CT01

The local scaffold provides one synthetic A4 template (`demo`). The large warning
on its page is part of the PDF itself. It is not a CT01/NA5 mapping, a legal form,
or a resolved official edition. Use fictional values only. The feature is disabled
by default; the application explicitly passes `demo_enabled=True` to opt in.

## HTTP contract

`GET /v1/forms/demo` returns field labels, limits, layout and template version.
`POST /v1/forms/demo/preview` returns a PNG raster of the rendered PDF.
`POST /v1/forms/demo/pdf` returns the same renderer's PDF and requires acknowledgement.

Both POST requests accept:

```json
{
  "values": {
    "full_name": "Nguyễn Thị Ánh Dương",
    "date_of_birth": "1995-06-15",
    "nationality": "Việt Nam",
    "address": "12 Đường Minh Họa",
    "phone_number": "+84 000 000 000",
    "email": "demo@example.invalid"
  },
  "revision": 2,
  "acknowledged": false,
  "template_version": "synthetic-demo-v1"
}
```

Use `acknowledged: true` only for the data currently reviewed. The UI must clear
the preview/acknowledgement after every edit, capture an immutable values/revision
snapshot for preview, ignore stale asynchronous responses and send that snapshot
for download. The server rejects changed template versions. Revision is a caller
correlation number, not an authorization token or server-stored profile revision;
the stateless demo cannot prove the user actually viewed a previous image.

Fields are optional strings or null (rendered blank). Limits match the profile model: name 120,
nationality 80, address 300, phone 32, email 254 and ISO date 10. Revision starts at one. Allowed length
does not guarantee physical fit: a long single line or address exceeding its
three lines gets a field-level 422 `text_overflow`, never clipping or tiny text.
Unknown IDs are 404; drafts and stale reviews are unavailable; preview/download
are transient, carry `Cache-Control: no-store, private` and write no user values
to disk. No form request is sent to a model or a government service.

## Coordinate and Unicode policy

- Units: PDF points (1/72 inch). Origin: top-left of unrotated page, x right/y down.
- Page indices are zero-based. Current layout supports one unrotated A4 page.
- Values start five points inside each rule. Font ascender/descender metrics
  position the entire text box at least three points above the dotted rule.
- Preview rasterizes the exact generated PDF at 120 DPI; it has no second layout.
- The actual Unicode font bytes are embedded. The renderer checks every value's
  glyphs without fallback and normalizes Vietnamese text to NFC. Unsupported
  glyphs are a visible 422, never a silent replacement square.
- Set `HOSO_FORM_FONT_PATH` to an explicitly installed Vietnamese-capable font.
  Without it, discovery tries the repository assets font path, the Codex bundled
  Poppler DejaVu Sans font, common Linux DejaVu Sans paths and Windows DejaVu Sans.
  Fonts with ambiguous space/hyphen mappings (including the tested Windows Arial)
  are rejected so copying/extracting values does not silently change codepoints. There is no network
  font download or silent Helvetica substitution. An invalid explicit setting
  yields service-unavailable rather than trying another font.

## Future official template gate

The trusted registry accepts only server-defined template IDs and PDF bytes;
HTTP never accepts a filesystem path. A real template must carry a human review
bound to the original source SHA-256, converted PDF SHA-256 and field-mapping
SHA-256, reviewer and review time. Any changed hash invalidates it. No API marks
a template reviewed. There is no official template in the shipped registry.
The first real implementation must add source/version provenance, its reviewed
mapping, and authorized owner/session routes before handling real personal data.
Current synthetic endpoints intentionally have no account-backed records.

Generic field discovery, automatic approval, digit-box/checkbox mapping and
multi-page/rotated official layouts are not implemented by this text-only seam.

## Verification

Run `python -m pytest api/tests/test_forms.py` in the configured API environment.
The tests generate real in-memory PDFs and PNGs, check extracted Vietnamese text,
measured/extracted baselines above dotted rules, wrapping/overflow refusal,
feature gating, review hash invalidation and the preview/download HTTP contract.
Human visual inspection is still required for each future official mapping.

Observed on 31 October 2026: all 15 forms tests passed, and the combined API suite
passed 62 tests. A fake-data rendered page was visually inspected at 120 DPI:
Vietnamese text, two-line address wrapping, the warning banner and separation
above the dotted rules were legible without overlap. These results establish the
synthetic renderer behavior only; they do not approve an official form. Runtime:
Python 3.12.14, PyMuPDF 1.28.2, bundled DejaVu Sans.

Renderer API references: [PyMuPDF Font](https://pymupdf.readthedocs.io/en/latest/font.html)
and [PyMuPDF Page](https://pymupdf.readthedocs.io/en/latest/page.html).
