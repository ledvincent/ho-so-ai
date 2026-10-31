# CT01 official-background test fixture

Purpose: an isolated UI checkpoint at `/demo/ct01`, using fictional values only. This is not a production registry entry, an approved field mapping, a complete application, or legal/form approval.

## Provenance

- Official source URL: https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/7/45606/57795-1-2025981-98255-2021-tt-bca.pdf
- Source document: 24-page Official Gazette PDF; source pages 6 and 7 (zero-based), printed pages 9 and 10.
- Printed source identification: Cong Bao 981 + 982, 26 July 2025. CT01 is headed as issued with Circular 53/2025/TT-BCA, dated 1 July 2025.
- Source SHA-256, from the supplied extraction manifest: `d7d587ff9a6a3bf1bb213e77f309f15a613c7eb17a63b69a79eb6c04bb70a098`.
- `blank-test-fixture.pdf`: unchanged two-page extract, 595.32 x 842.04 PDF points, no AcroForm fields. SHA-256 verified after copying: `ba72c63d656c2b3b0702faaef3f7a51c0356847631f16b47e7c354b8f5965444`.
- `page-1.png`: unchanged Poppler 120-dpi preview. SHA-256: `897280428cce8b9ffb6247ad3d22b2faf8d93c203565aeb0848b089a9df7c9ae`.
- `page-2.png`: unchanged Poppler 120-dpi preview. SHA-256: `787f70086973986210e351153f44a2a50ea5aa506b2283e94cbdcd0317fe7b8b`.
- Both blank page previews were visually inspected in this UI task. The second page's complete instructions remain present.

## Mapping and limits

`mapping.json` records the three-field overlay coordinates used by this test. Its UTF-8/LF byte SHA-256 is `16fd8e3db04f4e1b7dec8eb7043f11a7e174b1cc642af7ce2005240ec6552fc5`. The directory attributes preserve LF for this file.

Only name, date of birth and personal ID are overlaid on page one. Personal ID is a document-local string, preserving leading zeroes; it is not added to the shared six-field profile. Unmapped receiving authority, gender, contact details, household details, requests, opinions and signatures remain blank. There is no validation of real identity or eligibility.

Coordinates originate in the supplied research-only overlay measurements. The UI uses Times New Roman for mapped text, checks name width before allowing print, and refuses ambiguous dates. Browser layout and print parity require visual QA; unit tests alone do not approve this mapping. Any coordinate/font/fixture change requires a new mapping review and hash.

## Printing

The UI's print action uses an acknowledged immutable snapshot. Any edit invalidates it. Browser printing includes both original page images, adds the three values to page one, and adds an explicit test stamp in the bottom margin of each page. Page two's instruction content is unchanged.

This is browser Print / Save as PDF, not a direct PDF download or a fillable PDF. Use A4, 100% scale, and disable browser-generated headers/footers. The raster preview is test quality (120 dpi). No synthetic backend PDF, profile save, authentication exchange, external AI, submission, migration or production activation is performed.
