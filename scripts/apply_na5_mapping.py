"""Promote a validated model result to a DRAFT workflow, never to approval."""
import argparse
import copy
import hashlib
import json
import shutil
from api.config import ROOT,engine
from api.storage import write_json,export_shared_form
from api.attachments import save_mapping
from api.field_mapping import validate_mapping
from sqlalchemy import text


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--pdf',required=True);args=parser.parse_args()
    run=json.loads((ROOT/'data/forms/NA5/model-run.json').read_text(encoding='utf-8'))
    validate_mapping(run['result'],run['measured'])
    rendered=ROOT/args.pdf
    if hashlib.sha256(rendered.read_bytes()).hexdigest()!=run['inputs']['pdf_sha256']:
        raise ValueError('Model result belongs to a different rendered PDF')
    path=ROOT/'data/forms/NA5/workflow.json'
    old=json.loads(path.read_text(encoding='utf-8'))
    if old['review_status']=='reviewed':raise ValueError('Explicitly reopen template review before changing an approved map')
    folder=ROOT/'data/forms/_objects'/run['inputs']['sha256']
    target=folder/'blank.pdf'
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=run['inputs']['pdf_sha256']:
        history=folder/'renderings';history.mkdir(exist_ok=True)
        previous=history/(hashlib.sha256(target.read_bytes()).hexdigest()+'.pdf')
        if not previous.exists():shutil.copyfile(target,previous)
    shutil.copyfile(rendered,target)
    fields=copy.deepcopy(run['fields'])
    # UI compatibility aliases; the raw model result remains untouched.
    aliases={'host_type':{'family_sponsor':'family','family_relative':'family'},'sponsor_kind':{'foreign_national':'foreign_resident'}}
    previous={f['id']:f for f in old['fields']}
    for f in fields:
        if f['id'] in aliases:f['options']=[aliases[f['id']].get(v,v) for v in f['options']]
        f['when']={k:aliases.get(k,{}).get(v,v) for k,v in f.get('when',{}).items()}
        f['source_required']=f['required']
        # Application completeness requirements are a workflow policy, not a
        # claim that every blank is legally mandatory on the printed source.
        f['required']=previous.get(f['id'],{}).get('required',False)
        f['required_basis']='workflow completeness policy' if f['required'] else 'optional/manual'
        if f['id'] in ('visa_entries','visa_valid_until'):f['inactive']=True
        if f['id']=='request_type':f.update(hidden=True,required=True)
    metadata={**run['metadata'],'cache_path':run['cache_path'],'input_fingerprint':run['input_fingerprint']}
    mapping={**old,'fields':fields,'review_status':'draft','reviewed_by':None,'reviewed_at':None,
        'pdf_sha256':run['inputs']['pdf_sha256'],'pdf_path':target.relative_to(ROOT).as_posix(),
        'fixed_values':{'request_type':'stay_extension'},'mapping_metadata':metadata,'mapping_issues':run['result']['issues'],
        'rendering':{'engine':'LibreOffice','fonts':'Windows Times New Roman, read-only host font mount'},
        'notes':'Model-derived mapping; workflow completeness rules are separate from source requiredness. Original wording and all pages preserved. Signatures/stamps are manual.'}
    save_mapping(mapping['form_sha256'],dict(pdf_path=mapping['pdf_path'],fields=run['fields'],issues=run['result']['issues'],mapping_metadata=metadata))
    write_json(path,mapping)
    export_shared_form(mapping['form_sha256'])
    print('Installed draft:',len(fields),'logical fields;',len(run['measured']['anchors']),'measured writable anchors. Human review still required.')


if __name__=='__main__':main()
