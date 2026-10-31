"""Install a mapped official-copy form as a DRAFT, bound to its recorded procedures.

This never approves legal applicability or final downloads. Review the rendered
pages and mapping issues before use. Unknown/ambiguous associations are rejected.
"""
import argparse
import hashlib
import json
import re

from api.config import ROOT
from api.field_mapping import validate_mapping, compile_fields
from api.form_registry import REGISTRY_PATH, entries, local_file


def install(family, mapping_path, name):
    manifest=json.loads((ROOT/'data/forms/official-copies.json').read_text(encoding='utf8'))
    matches=[r for r in manifest if r['family']==family and r.get('document_kind')=='blank_form']
    if len(matches)!=1: raise ValueError('Expected one unambiguous recorded official copy')
    source=matches[0]
    saved=json.loads(local_file(mapping_path).read_text(encoding='utf8'))
    pdf=local_file(source['pdf_path'],ROOT/'data/forms')
    digest=hashlib.sha256(pdf.read_bytes()).hexdigest()
    if saved['inputs']['sha256']!=source['record']['sha256'] or saved['inputs']['pdf_sha256']!=digest:
        raise ValueError('Mapping does not match the recorded form bytes')
    result=validate_mapping(saved['result'],saved['measured'])
    fields=compile_fields(result,saved['measured'])
    codes=sorted({m['procedure_code'] for m in source.get('matches',[])})
    if not codes: raise ValueError('No recorded procedure association')
    registry=entries()
    installed=[]
    for code in codes:
        document_id=re.sub(r'[^a-z0-9-]+','-',family.lower())+'-'+code.replace('.','-')
        if any(r['document_id']==document_id for r in registry):
            raise ValueError('Document already installed; review an explicit version update instead')
        target=ROOT/'data/forms/workflows'/f'{document_id}.json'
        if target.exists(): raise ValueError('Workflow file already exists')
        mapping=dict(procedure_code=code,form_sha256=source['record']['sha256'],
            pdf_path=source['pdf_path'],pdf_sha256=digest,review_status='draft',reviewed_by=None,
            reviewed_at=None,revision_reference=source.get('revision') or 'Edition not printed',
            fields=fields,notes=result['issues'],mapping_metadata=saved['metadata'],
            source_provenance={key:source.get(key) for key in ('page_url','download_url','summary','matches')})
        entry=dict(document_id=document_id,form_id=family,procedure_code=code,name=name,
            spec_path=target.relative_to(ROOT).as_posix(),applicability='unresolved',
            requirement_names=[source['summary']])
        installed.append((entry,target,mapping))
    # Complete validation before touching the installed catalog.
    for entry,target,mapping in installed:
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        registry.append(entry)
    pending=REGISTRY_PATH.with_suffix('.pending.json')
    pending.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    pending.replace(REGISTRY_PATH)
    return [entry['document_id'] for entry,_,_ in installed]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family',required=True)
    parser.add_argument('--mapping',required=True)
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    print(json.dumps({'installed_drafts':install(args.family,args.mapping,args.name)}))


if __name__=='__main__':main()
