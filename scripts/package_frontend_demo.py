"""Package the current local demo and public procedure database, excluding secrets."""
import hashlib
import csv
import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import httpx

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/kim-handoff'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reuse-database',action='store_true',help='Keep an already restore-tested dump')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    def save(name,value):
        (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with httpx.Client(base_url='http://127.0.0.1:8001',timeout=30) as client:
        for name,url in [('openapi.json','/openapi.json'),('na5-schema.json','/documents/na5-provincial-stay-extension/schema'),
                         ('fictional-values.json','/documents/na5-provincial-stay-extension/example')]:
            response=client.get(url);response.raise_for_status();save(name,response.json())
        response=client.get('/assistant/setup');response.raise_for_status()
        setup=response.json()
    schema=json.loads((OUT/'na5-schema.json').read_text(encoding='utf-8'))
    with (OUT/'na5-fields.csv').open('w',encoding='utf-8-sig',newline='') as target:
        keys=['id','label','type','group','required','when','options','manual','hidden','inactive','max_length']
        writer=csv.DictWriter(target,fieldnames=keys);writer.writeheader()
        for field in schema['fields']:
            writer.writerow({k:json.dumps(field[k],ensure_ascii=False) if isinstance(field.get(k),(dict,list))
                             else field.get(k,'') for k in keys})
    report=json.loads((ROOT/'output/assistant-documents-live/report.json').read_text(encoding='utf-8'))
    assert report['passed'], 'Only package a passing live result'
    save('live-smoke.json',report)
    for case_name,filename in [('documents_en','chat-documents-response.json'),
                               ('processing_en','chat-processing-response.json'),
                               ('broad_start','chat-clarification-response.json')]:
        case=next(c for c in report['cases'] if c['name']==case_name)
        # Reports deliberately omit signed state. This fixture is illustrative,
        # never replayable conversation state or applicant data.
        save(filename,{**case['response'],'retrieval_state':None})
    save('chat-request.json',dict(message="I'm confused about the paperwork. Can you walk me through what I need and help me with the form?",
                                  procedure_code='1.001146',history=[]))
    shutil.copyfile(ROOT/'docs/kim-start-here.md',OUT/'START-HERE.md')
    if args.reuse_database:
        assert (OUT/'procedure-db.dump').is_file(), 'No existing database dump'
    else:
        with (OUT/'procedure-db.dump').open('wb') as target:
            subprocess.run(['docker','compose','exec','-T','db','pg_dump','-U','hoso','-d','hoso',
                            '-Fc','--no-owner','--no-acl'],cwd=ROOT,stdout=target,check=True)
    roots=['api','docs','migrations','scripts','tests','data/procedures','data/forms',
           'data/baselines','data/reviews','data/runs','data/_store','data/raw','data/archive/raw']
    paths=set()
    for directory in roots:
        paths.update(p for p in (ROOT/directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
    for name in ['.env.example','.gitignore','pyproject.toml','uv.lock','alembic.ini',
                 'compose.yaml','candidates.yaml','README.md']:
        paths.add(ROOT/name)
    assert all(p.name!='.env' and '.git' not in p.parts for p in paths)
    # Fail closed on recognizable real provider keys; do not print a match.
    for p in paths:
        if p.suffix in ('.py','.json','.md','.txt','.yaml','.html','.js'):
            import re
            if re.search(rb'sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}',p.read_bytes()):
                raise RuntimeError('Potential credential detected; archive was not created')
    files={p.relative_to(ROOT).as_posix():p for p in paths}
    for p in OUT.iterdir():
        if p.is_file() and p.name!='manifest.json':files['handoff/'+p.name]=p
    manifest=dict(created_at=datetime.now(timezone.utc).isoformat(),
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
        base_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_snapshot=True,model=setup['model'],reasoning_effort=setup['reasoning_effort'],
        files={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in sorted(files.items())},
        excluded=['.env','credentials','.git','virtualenv','Ollama model weights','applicant records (not stored)'])
    save('manifest.json',manifest)
    files['handoff/manifest.json']=OUT/'manifest.json'
    archive=ROOT/'output/kim-backend-demo.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED) as zipfile:
        for name,p in sorted(files.items()):zipfile.write(p,name)
    with ZipFile(ROOT/'output/kim-api-contract.zip','w',ZIP_DEFLATED) as zipfile:
        for p in OUT.iterdir():
            if p.is_file() and p.suffix in ('.json','.md','.csv'):zipfile.write(p,p.name)
    print(json.dumps(dict(archive=str(archive),bytes=archive.stat().st_size,
                         sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=len(files))))


if __name__=='__main__':main()
