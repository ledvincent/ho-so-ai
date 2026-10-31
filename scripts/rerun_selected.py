"""One controlled batch, immutable before/after artifacts and a semantic diff."""
import json
import uuid
from datetime import datetime,timezone
from pathlib import Path
import yaml
from sqlalchemy import text
from api.config import ROOT,engine
from api.analysis import run
from api.baseline import ensure
from api.db import get_procedure
from api.storage import write_json,export_procedure
from api.comparisons import compare
from api.profiles import digest


def changes(before,after,path=''):
    if before==after:return []
    if isinstance(before,dict) and isinstance(after,dict):
        return [entry for key in sorted(set(before)|set(after)) for entry in changes(before.get(key),after.get(key),path+'/'+key)]
    return [dict(path=path or '/',before=before,after=after)]


def summary(p):
    profile=(p.get('structured_profile') or {}).get('profile')
    return dict(source_sha256=p['sha256'],full_procedure_sha256=digest(p['document_json']),
        procedure_name=p['name'],methods=p['methods'],requirements=p['requirements'],
        forms=[{k:f.get(k) for k in ('source_url','form_sha256','association_method','revision_reference')} for f in p['forms']],
        facts_ready=p['analysis']['facts_ready'],profile=profile)


def main():
    baseline=ensure()
    batch_id=str(uuid.uuid4())
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder=ROOT/'data/runs'/f'{stamp}-{baseline["id"][:12]}'
    folder.mkdir(parents=True,exist_ok=False)
    selected=yaml.safe_load((ROOT/'candidates.yaml').read_text(encoding='utf-8'))['procedures']
    manifest=dict(batch_id=batch_id,baseline_id=baseline['id'],status='running',selected_codes=[p['code'] for p in selected],procedures=[],started_at=datetime.now(timezone.utc).isoformat())
    write_json(folder/'batch.json',manifest)
    with engine().begin() as db:
        db.execute(text("INSERT INTO catalog_batch(id,baseline_id,status,report) VALUES (:id,:baseline,'running',CAST(:report AS jsonb))"),dict(id=batch_id,baseline=baseline['id'],report=json.dumps(manifest)))
    print('BATCH',folder.relative_to(ROOT).as_posix(),flush=True)
    profiles={}
    for item in selected:
        code=item['code'];before=get_procedure(code);destination=folder/code
        write_json(destination/'before.json',before)
        report=run(before['source_url'],attachment_page=item['attachment_page'],baseline=baseline,output_dir=destination,
                   fallback_html=ROOT/before['raw_path'],fallback_attachment_html=ROOT/'data/procedures'/code/'attachment-source.html',prior=before)
        entry=dict(code=code,status=report['status'],run_id=report['run_id'],baseline_id=report['baseline_id'],issues=report['issues'],acquisition=report['acquisition'])
        if report['status']=='failed':
            entry['error']=report.get('error');print(code,'FAILED',report.get('error'),flush=True)
        else:
            after=get_procedure(code);write_json(destination/'after.json',after)
            delta=changes(summary(before),summary(after))
            write_json(destination/'changes.json',delta)
            entry.update(changed_paths=[d['path'] for d in delta],source_changed=before['sha256']!=after['sha256'],
                full_procedure_changed=digest(before['document_json'])!=digest(after['document_json']),
                parser_before=before['parser_version'],parser_after=after['parser_version'],
                aliases=len(after['structured_profile']['profile']['aliases']),examples=len(after['structured_profile']['profile']['example_requests']),
                criteria=len(after['structured_profile']['profile']['decision_criteria']),
                citations=report['profile']['validation']['citations_verified'],facts_ready=after['analysis']['facts_ready'])
            profiles[code]=json.loads((destination/'profile/profile.json').read_text(encoding='utf-8'))
            print(code,report['status'],'profile validated;',entry['citations'],'citations;',entry['criteria'],'criteria',flush=True)
        manifest['procedures'].append(entry);write_json(folder/'batch.json',manifest)
    if len(profiles)==len(selected):
        try:
            compared=compare(profiles,baseline,folder/'comparison')
            write_json(folder/'comparisons.json',compared)
            with engine().begin() as db:
                for relationship in compared['relationships']:
                    db.execute(text('INSERT INTO procedure_comparison(batch_id,left_code,right_code,result) VALUES (:batch,:left,:right,CAST(:result AS jsonb))'),dict(batch=batch_id,left=relationship['left_code'],right=relationship['right_code'],result=json.dumps(relationship)))
            manifest.update(status='complete',comparisons=len(compared['relationships']),comparison_citations=compared['citations_verified'])
        except Exception as exc:
            manifest.update(status='comparison_failed',comparison_error=str(exc))
    else:manifest['status']='incomplete'
    manifest['completed_at']=datetime.now(timezone.utc).isoformat()
    write_json(folder/'batch.json',manifest)
    with engine().begin() as db:
        db.execute(text('UPDATE catalog_batch SET status=:status,report=CAST(:report AS jsonb) WHERE id=:id'),dict(id=batch_id,status=manifest['status'],report=json.dumps(manifest)))
    lines=['# Controlled procedure rerun','',f'Baseline: `{baseline["id"]}`',f'Batch: `{batch_id}`',f'Status: **{manifest["status"]}**','',
           '| Procedure | Result | Page bytes changed | Full procedure changed | Aliases / examples | Clarification criteria | Verified citations |',
           '| --- | --- | --- | --- | --- | --- | --- |']
    for p in manifest['procedures']:
        lines.append(f'| [{p["code"]}]({p["code"]}/profile/profile.json) | {p["status"]} | {p.get("source_changed","n/a")} | {p.get("full_procedure_changed","n/a")} | {p.get("aliases",0)} / {p.get("examples",0)} | {p.get("criteria",0)} | {p.get("citations",0)} |')
    lines+=['','Each procedure has before.json, after.json, changes.json, its complete evidence registry, raw model output, and validation results. The same schema, prompts, model configuration and ingestion code apply to every row.','',
            'Extraction validation checks structure and quote membership; it does not establish current legal validity. Failed fetches and replayed evidence are listed below. Generated aliases/examples are routing material only.','']
    for p in manifest['procedures']:
        lines+=['## '+p['code'],'']
        for a in p['acquisition']:
            lines.append('- '+a['mode']+': '+a['url']+(' — '+a['error'] if a.get('error') else ''))
        if p.get('error'):lines.append('- Extraction failed: '+p['error'])
        if p.get('changed_paths'):lines.append('- Changed sections: '+', '.join(p['changed_paths']))
        if p.get('parser_before')!=p.get('parser_after'):lines.append('- Parser changed: '+p.get('parser_before','unknown')+' -> '+p.get('parser_after','unknown')+'. Changes in captured text may reflect newly captured source panels, not a government rule change.')
        lines.append('')
    if manifest.get('comparison_error'):lines+=['Comparison failed: '+manifest['comparison_error']]
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write_json(ROOT/'data/runs/latest.json',dict(batch_id=batch_id,baseline_id=baseline['id'],status=manifest['status'],report=(folder/'REPORT.md').relative_to(ROOT).as_posix()))
    from scripts.summarize_batch import main as summarize_batch
    summarize_batch()
    print('RESULT',manifest['status'],(folder/'REPORT.md').relative_to(ROOT).as_posix(),flush=True)
    if manifest['status']!='complete':raise SystemExit(1)


if __name__=='__main__':main()
