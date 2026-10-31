import json
from fastapi.testclient import TestClient
from api.main import app
from api.config import ROOT
from api import rag

def main():
    results=[]
    with TestClient(app) as client:
        for code in ['1.003326','1.001146','1.003342','1.000771']:
            response=client.post('/procedures/'+code+'/context',json={'query':'steps'})
            assert response.status_code==200,response.text
            assert response.json()['evidence_status']['form_applicability']=='unresolved'
        request={'message':'I want to extend my stay'}
        response=client.post('/assistant/chat',json=request)
        results.append(dict(request=request,http_status=response.status_code,response=response.json()))
        for _ in range(4):
            body=response.json()
            if body.get('status')!='needs_clarification' or not body.get('choices'):break
            choices=body['choices'];choice=next((c for c in choices if c['id']=='1.001146'),next((c for c in choices if c['id']!='unknown'),choices[0]))
            request={'message':choice['label'],'clarification_answer':choice['id'],'retrieval_state':body['retrieval_state']}
            response=client.post('/assistant/chat',json=request)
            results.append(dict(request=request,http_status=response.status_code,response=response.json()))
        for question in ['How long does processing take?', 'What is the fee?', 'Which documents and NA5 edition do I need?']:
            request={'message':question,'procedure_code':'1.001146'}
            response=client.post('/assistant/chat',json=request)
            results.append(dict(request=request,http_status=response.status_code,response=response.json()))
    path=ROOT/'output/scoped-answer-check.json';path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    for r in results: print(r['http_status'],r['response'].get('status'),r['response'].get('answer',r['response'].get('detail')))
    assert all(r['http_status']==200 for r in results),str(path)
    print('Conversation trace:',path)
if __name__=='__main__':main()
