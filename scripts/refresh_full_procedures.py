"""Reparse saved primary evidence; no fetches, models or human review approvals."""
import json
import uuid
import re
import yaml
from sqlalchemy import text
from api.config import ROOT,engine
from api.parse import parse
from api.db import ingest,get_procedure
from api.analysis import chunks, facts_available
from api.storage import export_procedure

def main():
    selected = yaml.safe_load((ROOT/'candidates.yaml').read_text(encoding='utf-8'))['procedures']
    with engine().connect() as db:
        preferred_na5=db.execute(text("SELECT preferred_sha256 FROM form_family WHERE code='NA5'")).scalar_one()
    for entry in selected:
        old = get_procedure(entry['code'])
        parsed = parse((ROOT/old['raw_path']).read_bytes(),entry['code'],old['source_url'],old['fetched_at'].isoformat(),entry['expected_name'])
        sid,_ = ingest(parsed,old['audience'],old['raw_path'],activate=False)
        report = dict(old['analysis']['report'])
        available=facts_available(parsed)
        report.update(run_id=str(uuid.uuid4()),issues=list(parsed['issues']),status='needs_review',facts_ready=available)
        report['form_association'] = dict(method='filename_fallback',family='NA5',preferred_sha256=preferred_na5)
        # References are retained for internal provenance, not user-facing text.
        report['source_controls'] = [dict(method=f['method'],references=f['detail_refs']) for f in parsed['fees'] if f['detail_refs']]
        with engine().begin() as db:
            db.execute(text("INSERT INTO analysis_run(id,source_url,procedure_code,status,completed_at,report) VALUES (:id,:url,:code,'needs_review',now(),CAST(:report AS jsonb))"),dict(id=report['run_id'],url=old['source_url'],code=entry['code'],report=json.dumps(report)))
            db.execute(text("""INSERT INTO procedure_analysis(snapshot_id,run_id,sections,summary,issues,readiness,facts_ready)
                VALUES (:sid,:run,CAST(:sections AS jsonb),:summary,CAST(:issues AS jsonb),'needs_review',:facts)
                ON CONFLICT(snapshot_id) DO UPDATE SET run_id=excluded.run_id,sections=excluded.sections,issues=excluded.issues,readiness=excluded.readiness,facts_ready=excluded.facts_ready"""),dict(sid=sid,run=report['run_id'],sections=json.dumps(parsed['document']),summary=old['name'],issues=json.dumps(parsed['issues']),facts=available))
            # Current primary requirement links resolve to the shared preferred family version.
            for form in parsed['forms']:
                if re.fullmatch(r'NA5\.docx?',form['label'],re.I):
                    db.execute(text("UPDATE procedure_form SET form_sha256=:sha,fetched_at=:date,association_method='filename_fallback' WHERE snapshot_id=:sid AND source_url=:url"),dict(sha=preferred_na5,date=old['fetched_at'],sid=sid,url=form['url']))
            for section in parsed['document']['sections']:
                for position,body in enumerate(chunks(section['text_verbatim'])):
                    db.execute(text("INSERT INTO rag_chunk(snapshot_id,section,position,text_verbatim,source_url,locator,fetched_at) VALUES (:sid,:section,:position,:body,:url,:section,:date) ON CONFLICT DO NOTHING"),dict(sid=sid,section=section['heading'],position=position,body=body,url=old['source_url'],date=old['fetched_at']))
            db.execute(text('UPDATE procedure SET current_snapshot_id=:sid WHERE code=:code'),dict(sid=sid,code=entry['code']))
        export_procedure(entry['code'])
        print(entry['code'],len(parsed['document']['sections']),'full sections;',len(parsed['methods']),'complete method descriptions; forms remain draft')

if __name__=='__main__':
    main()
