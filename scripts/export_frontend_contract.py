"""Export live API contracts and a public-question response, with no signed state."""
import argparse
import json
from pathlib import Path
import httpx


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',default='http://127.0.0.1:8001')
    parser.add_argument('--report',type=Path,default=Path('output/assistant-documents-live/report.json'))
    parser.add_argument('--output',type=Path,default=Path('docs/contracts'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    def save(name,value):
        (args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with httpx.Client(base_url=args.base_url,timeout=30) as client:
        for name,url in [('openapi.json','/openapi.json'),
                         ('procedure-documents.json','/procedures/1.001146/documents')]:
            response=client.get(url);response.raise_for_status();save(name,response.json())
        actions=client.get('/procedures/1.001146/documents').json()['documents']
        for action in actions:
            response=client.get(action['schema_url']);response.raise_for_status()
            save(action['document_id']+'-schema.json',response.json())
    report=json.loads(args.report.read_text(encoding='utf-8'))
    case=next(c for c in report['cases'] if c['name']=='documents_en')
    assert case['passed']
    save('chat-request.json',dict(message=case['question'],procedure_code='1.001146',history=[]))
    save('chat-response.json',{**case['response'],'retrieval_state':None})
    print('Exported OpenAPI, document discovery/schema and a real chat example.')


if __name__=='__main__':main()
