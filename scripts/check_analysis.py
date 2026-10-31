"""Read-only local database/API smoke check for completed agent runs."""
import json
import yaml
import hashlib
from sqlalchemy import text
from fastapi.testclient import TestClient
from api.config import ROOT, engine
from api.main import app

def main():
    codes = [p['code'] for p in yaml.safe_load((ROOT/'candidates.yaml').read_text(encoding='utf-8'))['procedures']]
    reports = [json.loads((ROOT/'data/procedures'/code/'analysis.json').read_text(encoding='utf-8')) for code in codes]
    assert len(reports)==4
    mapping_failures=set()
    with TestClient(app) as client, engine().connect() as db:
        for report in reports:
            assert report['status'] != 'failed', report
            p = client.get('/procedures/'+report['code'])
            assert p.status_code==200
            assert p.json()['source_url']==report['url']
            result = client.post('/procedures/'+report['code']+'/context',json={'query':'unrelated routing words'})
            if result.status_code==200:
                assert result.status_code==200
                payload = result.json()
                assert payload['full_procedure']==p.json()['document_json']
                assert len(payload['submission_methods'])==len(p.json()['methods'])
                assert all(m['description_verbatim'] for m in payload['submission_methods'])
                assert 'showMoreDes' not in json.dumps(payload) and 'Xem chi tiết' not in json.dumps(payload,ensure_ascii=False)
            else:
                assert result.status_code==409  # known superseded source revision
            assert not (ROOT/'data/procedures'/report['code']/'forms').exists()
            assert db.execute(text('SELECT count(*) FROM rag_chunk WHERE snapshot_id=:sid'),dict(sid=p.json()['id'])).scalar_one()>0
            for doc in report['documents']:
                response = client.get('/forms/'+doc['sha256']+'/analysis')
                assert response.status_code==200 and response.json()['review_status']=='draft'
                if doc['status']=='mapping_failed':
                    # Retaining an exact download does not imply its field map
                    # passed. Keep this explicitly visible without treating the
                    # failed attempt as a successfully mapped document.
                    assert doc.get('error') and any(doc['error'] in issue for issue in report['issues'])
                    original=client.get('/forms/'+doc['sha256']+'/original')
                    assert original.status_code==200
                    assert hashlib.sha256(original.content).hexdigest()==doc['sha256']
                    mapping_failures.add(doc['sha256'])
                    continue
                assert len(response.json()['fields'])==doc['field_count']
                for key in ['pdf']:
                    assert (ROOT/doc[key]).is_file()
        assert client.get('/procedures/1.002411').status_code==404
        for table,col in [('source_page','raw_path'),('form','raw_path'),('form','pdf_path')]:
            for path in db.execute(text(f'SELECT {col} FROM {table} WHERE {col} IS NOT NULL')).scalars():
                assert (ROOT/path).is_file(),path
        for row in db.execute(text('SELECT sha256,raw_path FROM form')).mappings():
            response=client.get('/forms/'+row['sha256']+'/original')
            assert response.status_code==200
            assert hashlib.sha256(response.content).hexdigest()==row['sha256']
            assert row['sha256'][:12] in response.headers['content-disposition']
    print('PASS: full captured records retained, known stale context gated, shared forms, draft fields, inactive procedure, all file paths')
    if mapping_failures:print('Unresolved legacy form mappings (not approved for filling): '+', '.join(sorted(mapping_failures)))

if __name__=='__main__':
    main()
