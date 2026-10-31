"""Capture a small allowlist of official pages. Nothing captured is auto-published."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from bs4 import BeautifulSoup

BASE = "https://vpcp.dichvucong.gov.vn/p/home/"
HOSTS = {"vpcp.dichvucong.gov.vn", "csdl.dichvucong.gov.vn"}
MAX_BYTES = 15 * 1024 * 1024
REQUIRED = {"Trình tự thực hiện", "Cách thức thực hiện", "Thành phần hồ sơ"}


def official_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in HOSTS or parts.port not in (None, 443) or parts.username or parts.password:
        raise ValueError(f"URL outside the source allowlist: {url}")
    return url


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Downloader:
    def __init__(self):
        self.last_request = 0.0
        self.opener = build_opener(OfficialRedirects())

    def get(self, url):
        official_url(url)
        time.sleep(max(0, 2 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        request = Request(url, headers={"User-Agent": "HoSoAI-Hackathon/0.1 (small official-source snapshot)"})
        with self.opener.open(request, timeout=20) as response:
            official_url(response.url)
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Download exceeds the 15 MiB limit")
            return body, {
                "source_url": url, "resolved_url": response.url,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "content_type": response.headers.get("Content-Type", ""),
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
            }


def text(node):
    # Preserve wording; only HTML entities and presentation whitespace change.
    return node.get_text(" ", strip=True)


def inspect_page(body, url, expected_name, code, detail=False):
    soup = BeautifulSoup(body, "html.parser")
    for node in soup(["script", "style"]):
        node.decompose()
    titles = [text(node) for node in soup.select("h1") if text(node)]
    if not any(expected_name.casefold() in title.casefold() for title in titles):
        raise ValueError("Procedure title missing/mismatched: possible app shell or wrong page")
    if detail and not re.search(r"(?<![\d.])" + re.escape(code) + r"(?![\d.])", text(soup)):
        raise ValueError("Detail page does not contain the expected national procedure code")
    sections = []
    for heading in soup.select("h2.main-title-sub"):
        siblings = []
        for node in heading.next_siblings:
            if getattr(node, "name", None) == "h2":
                break
            if "divider-gray" in getattr(node, "attrs", {}).get("class", []):
                break
            if getattr(node, "name", None) and text(node):
                siblings.append(text(node))
        sections.append({"heading": text(heading), "text_verbatim": "\n".join(siblings)})
    missing = sorted(REQUIRED - {section["heading"] for section in sections if section["text_verbatim"]})
    # Comparison pages may omit steps server-side. Keep the evidence but flag
    # incompleteness; never pretend agency/footer text is a missing steps section.
    mandatory = REQUIRED - {"Trình tự thực hiện"} if detail else REQUIRED
    if not mandatory.issubset({section["heading"] for section in sections if section["text_verbatim"]}):
        raise ValueError("Required procedure sections missing or empty; capture rejected")
    forms, detail_url, references = {}, None, {}
    for anchor in soup.select("a[href]"):
        href = urljoin(url, anchor["href"])
        parts = urlsplit(href)
        if parts.hostname == "csdl.dichvucong.gov.vn" and parts.path == "/web/jsp/download_file.jsp":
            if parse_qs(parts.query).get("ma", [""])[0].strip():
                official_url(href)
                forms[href] = {"source_url": href, "label": text(anchor)}
        if parts.hostname == "vpcp.dichvucong.gov.vn" and parts.path.endswith("/dvc-tthc-thu-tuc-hanh-chinh-chi-tiet.html"):
            if text(anchor) == "Xem chi tiết":
                detail_url = official_url(href)
        if parts.scheme in {"https", "http"} and re.search(r"\d{1,4}/\d{4}/|Luật|Nghị định|Thông tư", text(anchor)):
            references[href] = {"source_url": href, "label": text(anchor), "review_status": "unverified_reference"}
    # Some detail pages use onclick handlers, not links. Record these IDs without
    # executing JavaScript or guessing the download service behind getUrlDownload().
    unresolved_forms = {}
    for node in soup.select("[onclick]"):
        match = re.fullmatch(r"downloadMaudon\('([a-zA-Z0-9_-]+)'\);?", node["onclick"].strip())
        if match:
            unresolved_forms[match[1]] = {"portal_file_id": match[1], "label": text(node),
                                         "status": "download_url_needs_verification"}
    legal_basis = []
    for label in soup.select(".info-row .key"):
        if text(label).rstrip(": ") == "Căn cứ pháp lý":
            for row in label.parent.select("tbody tr"):
                cells = [text(cell) for cell in row.select("td")]
                if len(cells) == 4:
                    legal_basis.append(dict(zip(("number", "title", "issued_date", "issuer"), cells)))
    return {"title": titles[-1], "sections": sections, "form_links": list(forms.values()),
            "unresolved_form_links": list(unresolved_forms.values()), "legal_basis": legal_basis,
            "missing_sections": missing,
            "detail_url": detail_url, "legal_reference_links": list(references.values())}


def form_extension(body):
    if body.startswith(b"%PDF-"):
        return ".pdf"
    if body.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return ".doc"
    if body.startswith(b"PK\x03\x04"):
        # A ZIP response is a Word form only when the expected DOCX files exist.
        from io import BytesIO
        from zipfile import ZipFile
        with ZipFile(BytesIO(body)) as archive:
            if {"[Content_Types].xml", "word/document.xml"}.issubset(archive.namelist()):
                return ".docx"
    raise ValueError("Response is not a supported Word/PDF form (possibly an HTML error)")


def save_raw(root, body, metadata, extension):
    relative = Path("raw") / (metadata["sha256"] + extension)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(body)
    metadata["raw_path"] = relative.as_posix()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def capture(procedure, root, downloader):
    code = procedure["code"]
    url = BASE + "dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc=" + code
    report = {"procedure_code": code, "review_status": "draft", "parser_version": 1,
              "pages": [], "forms": [], "errors": [],
              "review_required": ["Resolve differences between by-code and detail pages; never merge silently.",
                                  "Check legal validity and the exact form edition before publishing."]}
    body, source = downloader.get(url)
    parsed = inspect_page(body, url, procedure["name"], code)
    save_raw(root, body, source, ".html")
    report["pages"].append({**source, **parsed, "kind": "by_code"})
    if parsed["detail_url"]:
        try:
            body, source = downloader.get(parsed["detail_url"])
            detail = inspect_page(body, source["source_url"], procedure["name"], code, detail=True)
            save_raw(root, body, source, ".html")
            report["pages"].append({**source, **detail, "kind": "detail_comparison_only"})
        except Exception as error:
            report["errors"].append({"stage": "detail", "message": str(error)})
    links = {link["source_url"]: link for page in report["pages"] for link in page["form_links"]}
    for url, link in links.items():
        try:
            body, source = downloader.get(url)
            save_raw(root, body, source, form_extension(body))
            report["forms"].append({**source, "label": link["label"], "review_status": "draft"})
        except Exception as error:
            report["errors"].append({"stage": "form", "source_url": url, "message": str(error)})
    # Only an explicit future human review workflow can publish these captures.
    write_json(root / "captures" / f"{code}.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=Path("coverage.json"))
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--code", action="append", help="Only fetch this allowlisted code; may repeat")
    parser.add_argument("--include-stretch", action="store_true")
    args = parser.parse_args()
    coverage = json.loads(args.coverage.read_text(encoding="utf-8"))["procedures"]
    if args.code and set(args.code) - {p["code"] for p in coverage}:
        parser.error("Requested code is not in coverage.json")
    selected = [p for p in coverage if (p["code"] in args.code if args.code else p["tier"] == "core" or args.include_stretch)]
    downloader = Downloader()
    failures = []
    for procedure in selected:
        try:
            report = capture(procedure, args.output, downloader)
            print(f'{procedure["code"]}: {len(report["pages"])} pages, {len(report["forms"])} form downloads, {len(report["errors"])} errors; DRAFT')
            failures.extend(report["errors"])
        except Exception as error:
            failures.append({"code": procedure["code"], "message": str(error)})
            print(f'{procedure["code"]}: FAILED: {error}')
    write_json(args.output / "captures" / "last_run.json", {"errors": failures, "completed_at": datetime.now(timezone.utc).isoformat()})
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
