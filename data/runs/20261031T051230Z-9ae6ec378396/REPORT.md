# Controlled procedure analysis report

Status: **complete**
Baseline: `9ae6ec3783961087c6c88c9c6e2a01ba75d9dd2d412fe43413901322f74386c9`
Batch: `089742a3-2445-454e-8837-73856748abab`

All selected procedures use the same ingestion code, profile schema, prompts, model settings and validation rules. Each procedure has before/after snapshots, semantic changes, complete source evidence, model responses and validation results.

## Source changes versus extraction changes

| Procedure | Live primary | Page bytes changed | Existing section text changed | Newly captured sections |
| --- | --- | --- | --- | --- |
| [1.003326](1.003326/profile/profile.json) | live | False | 0 | Thông tin dịch vụ và đối tượng thực hiện |
| [1.001146](1.001146/profile/profile.json) | live | False | 0 | Thông tin dịch vụ và đối tượng thực hiện |
| [1.003342](1.003342/profile/profile.json) | live | False | 0 | Thông tin dịch vụ và đối tượng thực hiện |
| [1.000771](1.000771/profile/profile.json) | live | False | 0 | Thông tin dịch vụ và đối tượng thực hiện |

The parser now also captures the portal service-selection panel, which explicitly identifies audience and authority level. Newly captured text is distinguished from changed wording in an existing section. Fetch time is never substituted for a government update/effective date.

## Structured extraction

| Procedure | Aliases / examples | Clarification criteria | Supported / unknown / conflicting facts | Verified citations |
| --- | --- | --- | --- | --- |
| 1.003326 | 4 / 6 | 14 | 71 / 20 / 7 | 239 |
| 1.001146 | 4 / 6 | 10 | 65 / 19 / 10 | 208 |
| 1.003342 | 4 / 6 | 12 | 114 / 23 / 4 | 248 |
| 1.000771 | 6 / 6 | 7 | 69 / 16 / 6 | 189 |

All requested profile categories are included. Unknown values remain null/unknown rather than guessed. Generated aliases, requests and question wording are labelled; they are not legal evidence. Quote validation establishes source membership, not legal correctness or currency.

## Catalog distinctions

- **1.000771 / 1.001146** — different_applicant_basis: The published stay bases differ: 1.000771 specifically requires entry using a visa exemption certificate, sponsorship in Vietnam and a legitimate reason; 1.001146 describes foreign nationals and Vietnamese people holding foreign passports with a visa unless exempt, temporary-stay certification and residence in Vietnam. This does not establish mutually exclusive eligibility.
- **1.000771 / 1.003326** — different_applicant_basis: 1.000771 expressly requires entry using a visa exemption certificate. 1.003326 describes a visa-or-exemption basis together with temporary-stay certification and residence in Vietnam. These are different published requirements; their overlap and interchangeability are not established.
- **1.000771 / 1.003342** — different_action: 1.000771 extends temporary stay for visa exemption certificate holders; 1.003342 issues a visa. Their published outcomes confirm this action difference.
- **1.001146 / 1.003326** — different_authority_level: Both procedures extend temporary stay, but the original identities expressly distinguish provincial implementation from central implementation. This establishes an authority-level difference, without establishing geographic routing rules or unrestricted choice between them.
- **1.001146 / 1.003342** — different_action: 1.001146 extends temporary stay at provincial level; 1.003342 issues visas at central level. Both action and authority level differ.
- **1.003326 / 1.003342** — different_action: Both identities specify central implementation, but 1.003326 extends temporary stay and 1.003342 issues visas. Their distinct published outcomes establish the action difference independently of shared forms.

Full two-sided citations and distinguishing criteria: [comparisons.json](comparisons.json). Shared NA5 usage never establishes procedural equivalence.

## Acquisition and outstanding review

### 1.003326

Result: blocked. Source facts ready for assistant context: False.

- live: https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.003326
- live: https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=26283
- download_failed: https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fd27ca760c23502 — Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fd27ca760c23502'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
- live_download: https://dichvucong.bocongan.gov.vn/public_dir/tttl/01/giayto/2022_07/1658255460_Mau-NA5--Don-xin-cap-visa-thi-thuc-Viet-Nam-2.doc
- Internal review issue: Attachment failed https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fd27ca760c23502: Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fd27ca760c23502'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503

[Before](1.003326/before.json) · [After](1.003326/after.json) · [Semantic changes](1.003326/changes.json) · [Evidence](1.003326/profile/sources.json)

### 1.001146

Result: blocked. Source facts ready for assistant context: False.

- live: https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.001146
- live: https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=36272
- download_failed: https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fe9f1715001aa84 — Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fe9f1715001aa84'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
- live_download: https://dichvucong.bocongan.gov.vn/public_dir/tttl/01/giayto/2022_06/1655667280_Mau-NA5--Don-xin-cap-visa-thi-thuc-Viet-Nam-2.doc
- Internal review issue: Attachment failed https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fe9f1715001aa84: Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fe9f1715001aa84'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503

[Before](1.001146/before.json) · [After](1.001146/after.json) · [Semantic changes](1.001146/changes.json) · [Evidence](1.001146/profile/sources.json)

### 1.003342

Result: blocked. Source facts ready for assistant context: False.

- live: https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.003342
- live: https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=26284
- download_failed: https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fdf7c9d43a8af50 — Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fdf7c9d43a8af50'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
- live_download: https://dichvucong.bocongan.gov.vn/public_dir/tttl/10/giayto/2020_11/1604957136_6-Mau_NA5.doc
- Internal review issue: Attachment failed https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fdf7c9d43a8af50: Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fdf7c9d43a8af50'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
- Internal review issue: Attachment failed https://dichvucong.bocongan.gov.vn/public_dir/tttl/10/giayto/2020_11/1604957136_6-Mau_NA5.doc: Date requires separate day/month/year: applicant_date_of_birth
- Internal review issue: Required form codes not found in downloaded files: NA5
- Internal review issue: Stored form mapping failed 3939f22cebb5464785832c5707678ca1166e02ad49c94e1ca3fe23234157b0e5: Date requires separate day/month/year: applicant_date_of_birth

[Before](1.003342/before.json) · [After](1.003342/after.json) · [Semantic changes](1.003342/changes.json) · [Evidence](1.003342/profile/sources.json)

### 1.000771

Result: blocked. Source facts ready for assistant context: False.

- live: https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=1.000771
- live: https://dichvucong.bocongan.gov.vn/bocongan/bothutuc/tthc?matt=26248
- download_failed: https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fb44fa49058e780 — Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fb44fa49058e780'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503
- live_download: https://dichvucong.bocongan.gov.vn/public_dir/tttl/01/giayto/2022_07/1658255460_Mau-NA5--Don-xin-cap-visa-thi-thuc-Viet-Nam-2.doc
- Internal review issue: Attachment failed https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fb44fa49058e780: Server error '503 Service Temporarily Unavailable' for url 'https://csdl.dichvucong.gov.vn/web/jsp/download_file.jsp?ma=3fb44fa49058e780'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503

[Before](1.000771/before.json) · [After](1.000771/after.json) · [Semantic changes](1.000771/changes.json) · [Evidence](1.000771/profile/sources.json)

