"""Atomically associate reviewed copies and append conservative profile relations.

Existing procedure facts and citations are copied verbatim. New form semantics
remain unknown until extraction/review; this operation never invokes a model.
"""
import copy
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
import pymupdf
from sqlalchemy import text

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from api.config import ROOT, engine
from api.form_recovery import verified_copies, recover_official, register_copy
from api.profiles import canonical, digest, validate_profile, validate_source_coverage
from api.storage import export_procedure, export_shared_form, write_json
from api.baseline import ensure


def relation(item, source):
    unknown=lambda:dict(value=None,status='unknown',source_refs=[],conflicts=[])
    result=dict(file_hash=item['record']['sha256'],aliases=[],
                required_when=dict(operator='unknown',criterion_key=None,values=[],children=[],source_refs=[]),
                completed_by=[],signed_by=[],certified_by=[],instructions=[],supporting_documents=[])
    for field in ('form_code','official_title','version','effective_from','effective_to'):result[field]=unknown()
    # Source edition is recorded, not asserted to be legally applicable today.
    if item.get('revision'):
        result['version']=dict(value=item['revision'],status='supported',source_refs=[dict(
            source_id=source['source_id'],locator=source['locator'],quote=source['text'])],conflicts=[])
    return result


def main():
    baseline=ensure()
    copies=verified_copies()
    # Retain ambiguous candidates in the inventory without assigning them.
    with engine().begin() as db:
        for item in copies:register_copy(db,item)
    codes=sorted({m['procedure_code'] for x in copies if not x.get('candidate_only') for m in x['matches']})
    result=[]
    for code in codes:
        with engine().begin() as db:
            sid=db.execute(text('SELECT current_snapshot_id FROM procedure WHERE code=:code FOR UPDATE'),dict(code=code)).scalar_one()
            head=dict(db.execute(text('''SELECT pp.* FROM procedure_profile_head h
                JOIN procedure_profile pp ON pp.id=h.profile_id WHERE h.snapshot_id=:sid'''),dict(sid=sid)).mappings().one())
            attachments=[dict(x) for x in db.execute(text('SELECT * FROM procedure_form WHERE snapshot_id=:sid'),dict(sid=sid)).mappings()]
            recovered=[]
            for a in attachments:
                r=recover_official(db,sid,code,dict(url=a['source_url'],label=a['label']),copies)
                if r.get('association_updated'):recovered.append(r)
            if not recovered:
                result.append(dict(code=code,status='unchanged'));continue
            hashes=set(db.execute(text('SELECT form_sha256 FROM procedure_form WHERE snapshot_id=:sid AND form_sha256 IS NOT NULL'),dict(sid=sid)).scalars())
            profile=copy.deepcopy(head['profile']);sources=copy.deepcopy(head['sources'])
            removed={x['file_hash'] for x in profile['form_relationships']}-hashes
            profile['form_relationships']=[x for x in profile['form_relationships'] if x['file_hash'] in hashes]
            sources=[s for s in sources if not (s['source_id'].startswith(('form:','registry:')) and s['sha256'] in removed)]
            old_enrichment={x['file_hash']:{k:x[k] for k in ('field_schema_ref','mapping_review_status','association_method') if k in x} for x in profile['form_relationships']}
            for rel in profile['form_relationships']:
                for key in ('field_schema_ref','mapping_review_status','association_method'):rel.pop(key,None)
            existing={x['file_hash'] for x in profile['form_relationships']}
            for sha in sorted(hashes-existing):
                item=next(x for x in copies if x['record']['sha256']==sha)
                registry=dict(source_id='registry:'+sha,locator='form-association',kind='registry',snapshot_id=sid,
                    url=item['download_url'],sha256=sha,fetched_at=item['record']['fetched_at'],
                    text=canonical({k:item.get(k) for k in ('family','summary','document_kind','revision','page_url','download_url','derivation','matching_basis','currency_note','matches')}))
                sources.append(registry)
                if item.get('pdf_path'):
                    with pymupdf.open(ROOT/item['pdf_path']) as pdf:
                        for n,p in enumerate(pdf,1):
                            body=p.get_text().replace('\x00','\ufffd').strip()
                            if len(body)>100:
                                sources.append(dict(source_id='form:'+sha,locator='page:'+str(n),kind='form',snapshot_id=sid,
                                    url=item['download_url'],sha256=sha,fetched_at=item['record']['fetched_at'],text=body))
                profile['form_relationships'].append(relation(item,registry))
            note='Official alternate form copies recovered; their applicability, completion rules and field mappings require review. Source procedure facts are unchanged.'
            if note not in profile['issues']:profile['issues'].append(note)
            profile,count=validate_profile(profile,sources,code,profile['official_name']['value'],hashes)
            validate_source_coverage(profile,sources)
            for rel in profile['form_relationships']:
                sha=rel['file_hash']
                rel.update(old_enrichment.get(sha,dict(field_schema_ref='data/forms/_objects/'+sha+'/fields.json',mapping_review_status='draft',association_method='official_copy')))
            run_id=str(uuid.uuid4())
            old_report=db.execute(text('SELECT report FROM analysis_run WHERE id=:id'),dict(id=head['run_id'])).scalar_one()
            report={**old_report,'run_id':run_id,'status':'blocked','baseline_id':baseline['id'],
                    'recovered_forms':recovered,'parent_run_id':str(head['run_id']),'operation':'recover_official_forms'}
            report['issues']=list(old_report.get('issues',[]))+[note]
            metadata=dict(extraction_status='validated_draft',parent_profile_id=head['id'],
                operation='append_verified_form_associations_v1',model_invoked=False,
                validation=dict(schema=True,citations_verified=count,identity=True,form_hashes=True),
                extracted_at=datetime.now(timezone.utc).isoformat())
            db.execute(text('''INSERT INTO analysis_run(id,source_url,procedure_code,status,baseline_id,completed_at,report)
                VALUES (:id,:url,:code,'blocked',:baseline,now(),CAST(:report AS jsonb))'''),dict(id=run_id,url=report['url'],code=code,baseline=baseline['id'],report=json.dumps(report)))
            pid=db.execute(text('''INSERT INTO procedure_profile(snapshot_id,run_id,baseline_id,profile,sources,metadata,output_sha256)
                VALUES (:sid,:run,:baseline,CAST(:profile AS jsonb),CAST(:sources AS jsonb),CAST(:meta AS jsonb),:sha) RETURNING id'''),
                dict(sid=sid,run=run_id,baseline=baseline['id'],profile=json.dumps(profile),sources=json.dumps(sources),meta=json.dumps(metadata),sha=digest(profile))).scalar_one()
            report['profile']=dict(profile_id=pid,output_sha256=digest(profile),validation=metadata['validation'])
            db.execute(text('UPDATE analysis_run SET report=CAST(:report AS jsonb) WHERE id=:run'),dict(run=run_id,report=json.dumps(report)))
            db.execute(text('UPDATE procedure_profile_head SET profile_id=:pid WHERE snapshot_id=:sid'),dict(pid=pid,sid=sid))
            db.execute(text('UPDATE search_text SET profile_id=:pid WHERE snapshot_id=:sid AND profile_id=:old'),dict(pid=pid,sid=sid,old=head['id']))
            db.execute(text("UPDATE procedure_analysis SET run_id=:run,readiness='blocked',issues=CAST(:issues AS jsonb) WHERE snapshot_id=:sid"),dict(run=run_id,sid=sid,issues=json.dumps(report['issues'])))
        write_json(ROOT/'data/_store/runs'/f'{run_id}.json',report)
        write_json(ROOT/'data/runs'/run_id/'analysis.json',report)
        export_procedure(code)
        result.append(dict(code=code,recovered_associations=len(recovered),profile_id=pid))
        print(code,len(recovered),'recovered',flush=True)
    for item in copies:export_shared_form(item['record']['sha256'])
    write_json(ROOT/'data/forms/recovery-report.json',result)


if __name__=='__main__':main()
