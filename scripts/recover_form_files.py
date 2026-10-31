"""Download, validate and stage explicitly sourced official form candidates."""
import json
import sys
import ssl
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.config import ROOT
from api.documents import store_document
from api.analysis import analyse_file

MANIFEST = ROOT / 'data/forms/recovery.json'


def stage(item):
    if item.get('record') and (ROOT/item['record']['raw_path']).exists():
        return item
    try:
        context = ssl.create_default_context()
        if item['download_url'].startswith('https://baohiemxahoi.gov.vn'):
            context.options |= 4  # Legacy server connect; certificate verification remains on.
        response = httpx.get(item['download_url'], timeout=45, follow_redirects=True, verify=context)
        response.raise_for_status()
        record = store_document(response.content, str(response.url), item['filename'])
        record.update(url=str(response.url), fetched_at=datetime.now(timezone.utc).isoformat())
        item['record'] = record
        result = analyse_file(record, use_model=False)
        item['pdf_path'] = result['pdf_path']
        item['page_count'] = len(result['pages'])
        folder = ROOT / record['raw_path']; folder = folder.parent
        (folder/'text.txt').write_text('\n\f\n'.join(result['pages']), encoding='utf-8')
        item.pop('error', None)
    except Exception as exc:
        item['error'] = str(exc)
    print(item['family'], item.get('error', item.get('record',{}).get('sha256')), flush=True)
    return item


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    items = json.loads(MANIFEST.read_text(encoding='utf-8'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        items = list(pool.map(stage, items))
    MANIFEST.write_text(json.dumps(items, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
