# Recommended hackathon scope

This is a proposed reduction of the original charter to make room for voice and
phone delivery. It is a product recommendation, not a claim about legal eligibility.

## One complete journey first

Caller describes a residence task -> agent clarifies registration versus renewal
-> reviewed procedure lookup -> checklist with sources -> mobile report link ->
reviewed CT01 preview/download, once the correct edition is verified.

| Priority | Procedure | Code | Release gate |
| --- | --- | --- | --- |
| First vertical slice | Temporary residence registration | 1.004194 | One working call, sourced checklist, mobile report |
| Core expansion | Temporary residence renewal | 1.002755 | Correctly distinguish it from registration |
| Stretch | Foreigner temporary residence extension | 1.001146 | Separate eligibility flow and reviewed NA5 |

Use Vietnamese first. Add English after the Vietnamese journey works. Choose one
phone delivery channel and send a private report link after confirming the user's
destination and consent. A website microphone is a useful integration fallback
while real inbound telephony is being connected; label that demo accurately.

Defer permanent residence, passports, identity cards, nationwide local variations,
automatic government submission, broad legal Q&A, and automatic field discovery.
For the first release, display the complete official document list including case
conditions. Do not claim to calculate a personalized legal checklist. An agent may
clarify intent but must not silently remove requirements based on its own reasoning.

## Three kinds of evidence

1. Procedure pages: steps, document requirements and quantities, fees with their
   conditions, processing times, agency, form links. Start with the small allowlist.
2. Official form files: keep original bytes, hash and source. Download does not mean
   approval. Convert and inspect the exact edition before any field mapping is live.
3. Underlying legal instruments: keep the cited number, title, issuing authority,
   issue date, official document URL and validity/amendment review separately.
   Resolve references through official sources such as https://vbpl.vn/ and
   https://vanban.chinhphu.vn/. Do not import an entire laws corpus for the demo.

The current fetcher implements source capture, form link discovery/download and
legal-basis inventory. Full law-document fetching and validity verification are
not implemented. Portal references alone do not establish a law's current effect.

## Observations from the first live capture

Checked on 31 October 2026:

- The old main-host by-code URL returned an app shell in a direct HTTP fetch.
- The `vpcp.dichvucong.gov.vn` by-code pages returned substantive HTML for both
  core procedures. This is the explicitly configured source, not a silent fallback.
- Registration's by-code page linked forms named `Mẫu CT01 _66.doc`, while its
  linked detail page named CT01 under `53/2025/TT-BCA`. Quantities also differ.
  Neither is automatically selected as legally current. A reviewer must resolve
  the conflict using the current official instrument and exact attachment.
- All six legacy form download URLs attempted in the initial run returned HTTP
  503. The newer detail-page forms expose JavaScript file IDs. Those IDs are
  inventoried, but their download endpoint still needs verification.

Sources:

- https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.004194
- https://vpcp.dichvucong.gov.vn/p/home/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html?ma_thu_tuc=5974
- https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.002755

## Publication gates and handoff

Vincent owns capture, structured parsing and source review. Son consumes reviewed
procedure records for search/voice. Kim consumes reviewed form hashes and field
maps, and builds the mobile report and delivery flow.

Next implementation steps:

1. Resolve the CT01 edition conflict and verify the official download endpoint.
2. Parse requirements as grouped rows with quantities, and fees as method/amount/
   condition rows. Preserve source wording; no LLM extraction of legal facts.
3. Give each fact procedure code, source URL, fetched_at, page hash and parser
   version. Store legal effective dates separately from retrieval dates.
4. Human review approves a specific source hash and exact form edition. Any source
   change requires new review. Until approval, records cannot feed the voice agent.
5. Expose reviewed records through one procedure lookup contract for both voice
   and the report. Keep user data out of the source corpus, logs and Git.

Success means one real or clearly labeled browser voice session produces the right
reviewed checklist and mobile report. A filled PDF is enabled only once its source
edition and coordinates pass review. Unsupported tasks explicitly say not covered.
