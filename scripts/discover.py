"""Bounded candidate inspection, not a crawler."""
import json
import time
import sys
from pathlib import Path
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup

BASE = 'https://dichvucong.bocongan.gov.vn'

def main():
    client = httpx.Client(timeout=45, follow_redirects=False)
    results = []
    for mid in sys.argv[1:] or ['26270', '29497', '26345', '26093', '26094', '52392', '36272']:
        time.sleep(2)
        url = BASE + '/bocongan/bothutuc/tthc?matt=' + mid
        r = client.get(url)
        r.raise_for_status()
        Path('tmp/mps-' + mid + '.html').write_bytes(r.content)
        s = BeautifulSoup(r.content, 'html.parser')
        if not s.select_one('h4'):
            print('Rejected empty detail page',mid,flush=True)
            continue
        sections = {x.select_one('.item-title').get_text(' ',strip=True):x.select_one('.tthc-list-item-detail').get_text(' ',strip=True) for x in s.select('.tthc-list-item') if x.select_one('.item-title') and x.select_one('.tthc-list-item-detail')}
        links = sorted({urljoin(url,a['href']) for a in s.select('a[href]') if '/public_dir/' in a['href']})
        item = dict(url=url, name=s.select_one('h4').get_text(' ',strip=True), code=sections.get('Mã thủ tục'), sections=sections, documents=[])
        for link in links:
            time.sleep(2)
            try:
                doc = client.get(link)
                item['documents'].append(dict(url=link,status=doc.status_code,size=len(doc.content),signature=doc.content[:8].hex()))
            except httpx.HTTPError as exc:
                item['documents'].append(dict(url=link,error=str(exc)))
        results.append(item)
        Path('tmp/discovery.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        print(item['code'],item['name'],[(d.get('status'),d.get('size')) for d in item['documents']],flush=True)

if __name__ == '__main__':
    main()
