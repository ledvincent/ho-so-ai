"""HTTP smoke check with fictional data; never approves the persisted template."""
import json
from unittest.mock import patch
import pymupdf
from fastapi.testclient import TestClient
from api.config import ROOT
from api.main import app
from api import na5

def main():
    values=json.loads((ROOT/'tests/fixtures/na5-example.json').read_text(encoding='utf-8'))
    with TestClient(app) as client:
        assert client.get('/workflows/1.001146').status_code==200
        schema=client.get('/workflows/1.001146/schema').json()
        assert schema['revision']=='70/2026/TT-BCA'
        preview=client.post('/workflows/1.001146/preview',json={'values':values})
        assert preview.status_code==200,preview.text
        token=preview.headers['X-Review-Token']
        request=dict(values=values,review_token=token,confirmed=True)
        assert client.post('/workflows/1.001146/download',json=request).status_code==409
        current=na5.spec()
        with patch('api.na5.spec',return_value={**current,'review_status':'reviewed'}):
            request['review_token']=client.post('/workflows/1.001146/preview',json={'values':values}).headers['X-Review-Token']
            response=client.post('/workflows/1.001146/download',json=request)
            assert response.status_code==200
            with pymupdf.open(stream=response.content,filetype='pdf') as pdf:
                assert len(pdf)==3 and 'ÉLODIE EXEMPLE' in pdf[0].get_text()
                assert 'TEMPLATE REVIEW DRAFT' not in pdf[0].get_text()
            request['values']={**values,'reason':'Modified after preview'}
            assert client.post('/workflows/1.001146/download',json=request).status_code==422
    assert na5.spec()['review_status']=='draft'
    print('PASS: form -> validated PDF preview -> checked download; changed values rejected; production remains gated until human template review')

if __name__=='__main__':main()
