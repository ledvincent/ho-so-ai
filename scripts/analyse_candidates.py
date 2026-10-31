import json
import yaml
from urllib.parse import urlparse,parse_qs
from api.analysis import run
from api.config import ROOT

def main():
    candidates = yaml.safe_load((ROOT/'candidates.yaml').read_text(encoding='utf-8'))
    reports = []
    for item in candidates['procedures']:
        url = 'https://vpcp.dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-nganh-doc.html?ma_thu_tuc='+item['code']
        mid = parse_qs(urlparse(item['attachment_page']).query)['matt'][0]
        saved = ROOT/'tmp'/f'mps-{mid}.html'
        report = run(url,attachment_page=item['attachment_page'],attachment_html=str(saved) if saved.exists() else None)
        reports.append(report)
        print(item['code'],report['status'],len(report['documents']),report.get('error',''),flush=True)
        destination = ROOT/'data/_store/candidates.json'
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__ == '__main__':
    main()
