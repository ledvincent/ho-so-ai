"""Group human-facing NA5 files; relocate immutable objects without copying them."""
import hashlib
import json
import re
import shutil
from pathlib import Path
from sqlalchemy import text
from api.config import ROOT,engine
from scripts.consolidate_documents import replace_paths


def main():
    root=(ROOT/'data/forms').resolve()
    objects=root/'_objects';objects.mkdir(exist_ok=True)
    family=root/'NA5';family.mkdir(exist_ok=True)
    moves=[]
    for path in root.iterdir():
        if path.is_dir() and re.fullmatch('[a-f0-9]{64}',path.name):moves.append((path,objects/path.name))
    for old,new in [('na5-2026.spec.json','workflow.json'),('na5-2026.source.json','source.json'),('na5-2026.review.json','review.json'),('na5-2026.model-run.json','model-run.json')]:
        if (root/old).exists():moves.append((root/old,family/new))
    aliases={}
    for source,target in moves:
        if not source.resolve().is_relative_to(root) or not target.resolve().is_relative_to(root):raise ValueError('Move escapes forms store')
        if target.exists():raise ValueError('Destination already exists: '+str(target))
        files=[source] if source.is_file() else [p for p in source.rglob('*') if p.is_file()]
        for file in files:
            destination=target if source.is_file() else target/file.relative_to(source)
            aliases[file.relative_to(ROOT).as_posix()]=destination.relative_to(ROOT).as_posix()
    # Save recovery instructions before any relocation.
    plan=ROOT/'tmp/forms-relocation.json';plan.parent.mkdir(exist_ok=True)
    plan.write_text(json.dumps(aliases,indent=2),encoding='utf-8')
    for source,target in moves:shutil.move(str(source),str(target))
    with engine().begin() as db:
        for before,after in aliases.items():
            db.execute(text('UPDATE form SET raw_path=:after WHERE raw_path=:before'),dict(before=before,after=after))
            db.execute(text('UPDATE form SET pdf_path=:after WHERE pdf_path=:before'),dict(before=before,after=after))
        for table,key,columns in [('form','sha256',['source_metadata','mapping_metadata']),('analysis_run','id',['report'])]:
            for row in db.execute(text(f'SELECT {key},{",".join(columns)} FROM {table}')).mappings():
                for column in columns:
                    new=replace_paths(row[column],aliases)
                    if new!=row[column]:db.execute(text(f'UPDATE {table} SET {column}=CAST(:value AS jsonb) WHERE {key}=:key'),dict(value=json.dumps(new),key=row[key]))
    for path in (ROOT/'data').rglob('*.json'):
        old=json.loads(path.read_text(encoding='utf-8'));new=replace_paths(old,aliases)
        if new!=old:path.write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf-8')
    index=root/'storage-aliases.json'
    old=json.loads(index.read_text(encoding='utf-8')) if index.exists() else {}
    index.write_text(json.dumps({**old,**aliases},indent=2),encoding='utf-8')
    # Storage-only changes do not alter any placements or the rendered review.
    review=family/'review.json'
    if moves and review.exists():
        info=json.loads(review.read_text(encoding='utf-8'))
        info['prior_spec_sha256']=info['spec_sha256']
        info['spec_sha256']=hashlib.sha256((family/'workflow.json').read_bytes()).hexdigest()
        info['storage_relocation']='Only storage references changed; field placements and reviewed PDF bytes unchanged.'
        review.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    from api.storage import export_shared_form,export_procedure
    with engine().connect() as db:
        hashes=list(db.execute(text('SELECT sha256 FROM form')).scalars())
        codes=list(db.execute(text('SELECT code FROM procedure WHERE active')).scalars())
    for sha in hashes:export_shared_form(sha)
    for code in codes:export_procedure(code)
    print('Organized forms:',len(moves),'moves;',len(aliases),'references relocated; original bytes unchanged.')


if __name__=='__main__':main()
