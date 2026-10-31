"""Only allowlisted GETs. Sequential requests, content-addressed storage."""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from api.config import ROOT, coverage


def allowed(url):
    u = urlparse(url)
    if u.scheme != "https" or u.port not in (None, 443) or u.username or u.password:
        return False
    if u.hostname in ("vpcp.dichvucong.gov.vn", "dichvucong.gov.vn"):
        codes = {p["code"] for p in coverage()["procedures"]}
        return u.path == "/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html" and parse_qs(u.query).get("ma_thu_tuc", []) in [[c] for c in codes]
    return (u.hostname == "csdl.dichvucong.gov.vn" and u.path == "/web/jsp/download_file.jsp"
            and bool(parse_qs(u.query).get("ma")))


class Fetcher:
    def __init__(self):
        self.last = 0.0
        self.client = httpx.Client(timeout=60, follow_redirects=False)

    def get(self, url, directory="raw"):
        if not allowed(url):
            raise ValueError("URL outside procedure/form allowlist")
        time.sleep(max(0, 2 - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        response = self.client.get(url)
        response.raise_for_status()  # Redirects require explicit inspection, too.
        raw = response.content
        if directory == "forms" and not (raw.startswith(b"PK\x03\x04") or raw.startswith(bytes.fromhex("d0cf11e0a1b11ae1")) or raw.startswith(b"%PDF-")):
            raise ValueError("Form response is not DOC, DOCX, or PDF")
        digest = hashlib.sha256(raw).hexdigest()
        folder = ROOT / 'data/_store' / ('html' if directory=='raw' else 'documents')
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / digest
        if not path.exists():
            path.write_bytes(raw)
        return dict(url=url, sha256=digest, fetched_at=datetime.now(timezone.utc).isoformat(),
                    raw_path=path.relative_to(ROOT).as_posix())


def fetch_pages():
    config = coverage()
    fetcher = Fetcher()
    manifest = {}
    for entry in config["procedures"]:
        code = entry["code"]
        manifest[code] = fetcher.get(config["source_base"] + "?ma_thu_tuc=" + code)
    path = ROOT / "data/_store/manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
