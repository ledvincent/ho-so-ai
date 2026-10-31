"""Inspect official pages for downloadable attachments; keep captured evidence."""
import hashlib
import json
import re
import sys
import ssl
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]


def inspect(url):
    try:
        context = ssl.create_default_context()
        if url.startswith('https://baohiemxahoi.gov.vn'):
            context.options |= 4
        response = httpx.get(url, timeout=35, follow_redirects=True, verify=context)
        response.raise_for_status()
        sha = hashlib.sha256(response.content).hexdigest()
        folder = ROOT / 'data/_store/form-sources'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / sha).write_bytes(response.content)
        soup = BeautifulSoup(response.content, 'html.parser')
        links = []
        for a in soup.select('[href], [src]'):
            target = urljoin(str(response.url), a.get('href') or a.get('src'))
            label = a.get_text(' ', strip=True)
            if re.search(r'\.(docx?|pdf|zip)(?:$|[?#])|download|TaiFile|GetFile', target, re.I):
                links.append(dict(url=target, label=label))
        return dict(page=url, final_url=str(response.url), sha256=sha, links=links)
    except Exception as exc:
        return dict(page=url, error=str(exc))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for result in ThreadPoolExecutor(max_workers=5).map(inspect, sys.argv[1:]):
        print(json.dumps(result, ensure_ascii=False))
