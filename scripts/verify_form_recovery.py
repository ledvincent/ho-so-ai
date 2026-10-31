"""Audit recovered links, immutable source facts, original bytes and PDF excerpts."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import pymupdf
from sqlalchemy import text

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from api.config import ROOT,engine
from api.form_recovery import verified_copies
from api.profiles import validate_profile,validate_source_coverage


def main():
    copies=verified_copies()
    for item in copies:
        record=item['record']
        assert hashlib.sha256((ROOT/record['raw_path']).read_bytes()).hexdigest()==record['sha256']
        if item.get('derivation'):
            source=item['derivation']
            assert hashlib.sha256((ROOT/source['original_path']).read_bytes()).hexdigest()==source['original_sha256']
            with pymupdf.open(ROOT/item['pdf_path']) as derived,pymupdf.open(ROOT/source['source_pdf_path']) as original:
                assert len(derived)==len(source['pages'])
                for i,n in enumerate(source['pages']):
                    assert derived[i].get_pixmap().samples==original[n-1].get_pixmap().samples,(item['family'],n)
    with engine().connect() as db:
        rows=[dict(x) for x in db.execute(text('''SELECT p.code,pp.* FROM procedure p
            JOIN procedure_profile_head h ON h.snapshot_id=p.current_snapshot_id
            JOIN procedure_profile pp ON pp.id=h.profile_id WHERE p.active''')).mappings()]
        verified=[]
        for row in rows:
            if row['metadata'].get('operation')!='append_verified_form_associations_v1':continue
            parent=db.execute(text('SELECT profile FROM procedure_profile WHERE id=:id'),dict(id=row['metadata']['parent_profile_id'])).scalar_one()
            for key,value in parent.items():
                if key not in ('form_relationships','issues'):assert row['profile'][key]==value,(row['code'],key)
            profile=copy.deepcopy(row['profile'])
            for rel in profile['form_relationships']:
                for key in ('field_schema_ref','mapping_review_status','association_method'):rel.pop(key,None)
            hashes=list(db.execute(text('SELECT DISTINCT form_sha256 FROM procedure_form WHERE snapshot_id=:sid AND form_sha256 IS NOT NULL'),dict(sid=row['snapshot_id'])).scalars())
            _,count=validate_profile(profile,row['sources'],row['code'],profile['official_name']['value'],hashes)
            validate_source_coverage(profile,row['sources'])
            verified.append(dict(code=row['code'],forms=len(hashes),citations=count))
        remaining=[dict(x) for x in db.execute(text('''SELECT p.code,pf.label,pf.source_url FROM procedure p
            JOIN procedure_form pf ON pf.snapshot_id=p.current_snapshot_id
            WHERE p.active AND pf.form_sha256 IS NULL ORDER BY p.code,pf.label''')).mappings()]
        for missing in remaining:
            candidates=[x for x in copies if x.get('candidate_only') and any(m['source_url']==missing['source_url'] for m in x['matches'])]
            missing['candidates']=[dict(sha256=x['record']['sha256'],path=x['record']['raw_path'],reason=x['currency_note']) for x in candidates]
        recovered=db.execute(text('''SELECT count(*) FROM procedure p JOIN procedure_form pf ON pf.snapshot_id=p.current_snapshot_id
            WHERE p.active AND pf.association_method='official_copy' ''')).scalar_one()
    result=dict(recovered_associations=recovered,verified_profiles=verified,unresolved=remaining,
                originals_hash_checked=True,derived_pages_render_identically=True,procedure_facts_unchanged=True)
    (ROOT/'data/forms/recovery-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
