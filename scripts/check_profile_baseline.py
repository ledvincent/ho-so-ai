"""Verify a completed common-baseline catalog, evidence, routing and storage."""
import hashlib
import json
from pathlib import Path
from sqlalchemy import text
from fastapi.testclient import TestClient
from api.config import ROOT,engine
from api.main import app
from api.profiles import validate_citations


def main():
    latest=json.loads((ROOT/'data/runs/latest.json').read_text(encoding='utf-8'))
    folder=(ROOT/latest['report']).parent
    manifest=json.loads((folder/'batch.json').read_text(encoding='utf-8'))
    assert manifest['status']=='complete',manifest['status']
    assert len(manifest['procedures'])==4 and manifest['comparisons']==6
    baseline=manifest['baseline_id']
    baseline_folder=ROOT/'data/baselines'/baseline
    contract=json.loads((baseline_folder/'manifest.json').read_text(encoding='utf-8'))
    for relative,expected in contract['source_code_sha256'].items():
        assert hashlib.sha256((baseline_folder/'source'/relative).read_bytes()).hexdigest()==expected
    with engine().connect() as db,TestClient(app) as client:
        for item in manifest['procedures']:
            code=item['code']
            response=client.get('/procedures/'+code+'/profile')
            assert response.status_code==200,response.text
            profile=response.json()
            assert profile['baseline_id']==baseline
            assert validate_citations(profile['profile'],profile['sources'])==item['citations']
            assert len(profile['related_procedures'])==3
            assert validate_citations(profile['related_procedures'],profile['comparison_sources'])>0
            for form in profile['profile']['form_relationships']:
                assert (ROOT/form['field_schema_ref']).is_file()
            count=db.execute(text('SELECT count(*) FROM search_text WHERE profile_id=:id'),dict(id=profile['id'])).scalar_one()
            assert count==item['aliases']+item['examples'],(code,count)
            assert (folder/code/'before.json').exists() and (folder/code/'changes.json').exists()
        originals=[]
        for form in db.execute(text('SELECT sha256,raw_path,pdf_path FROM form')).mappings():
            path=ROOT/form['raw_path'];assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest()==form['sha256']
            assert '/_objects/' in form['raw_path']
            originals.append(form['sha256'])
            if form['pdf_path']:assert (ROOT/form['pdf_path']).is_file()
        assert len(originals)==len(set(originals))
    print('PASS: four profiles share one baseline, six cited comparisons, generated routing, exact fingerprints and all references resolve.')


if __name__=='__main__':main()
