"""Consolidate verified byte-identical artifacts, retaining source provenance.

Run without --apply for a reviewable plan. Unknown/unique files are never removed.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from sqlalchemy import text
from api.config import ROOT, engine
from api.documents import file_extension


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_paths(value, aliases):
    if isinstance(value, str):
        return aliases.get(value, value)
    if isinstance(value, list):
        return [replace_paths(v, aliases) for v in value]
    if isinstance(value, dict):
        return {k:replace_paths(v, aliases) for k,v in value.items()}
    return value


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--apply',action='store_true'); args=parser.parse_args()
    with engine().connect() as db:
        forms = [dict(r) for r in db.execute(text('SELECT * FROM form')).mappings()]
        labels = {r['form_sha256']:r['label'] for r in db.execute(text('SELECT form_sha256,label FROM procedure_form WHERE form_sha256 IS NOT NULL')).mappings()}
    canonical, targets = {}, {}
    for form in forms:
        sha=form['sha256']; source=ROOT/form['raw_path']
        if digest(source)!=sha: raise ValueError('Stored fingerprint mismatch: '+str(source))
        label=labels.get(sha,'')
        family=re.search(r'\b(?:NA|TK|CT|CC|DC)\d{1,2}\b', label, re.I)
        stem=family[0].upper() if family else 'document'
        target=ROOT/'data/forms/_objects'/sha/f'{stem}--{sha[:12]}{file_extension(source.read_bytes())}'
        canonical[sha]=(source,target)
        pdf=ROOT/form['pdf_path'] if form['pdf_path'] else None
        pdf_target=(target if pdf and digest(pdf)==sha else target.parent/'blank.pdf') if pdf else None
        if pdf:canonical.setdefault(digest(pdf),(pdf,pdf_target))
        targets[sha]=dict(raw=target.relative_to(ROOT).as_posix(),pdf=pdf_target.relative_to(ROOT).as_posix() if pdf else None)
    aliases,duplicates={},[]
    for path in (ROOT/'data').rglob('*'):
        if not path.is_file() or path.suffix.lower() not in ('','.doc','.docx','.pdf'):continue
        entry=canonical.get(digest(path))
        if entry and path.resolve()!=entry[1].resolve():
            aliases[path.relative_to(ROOT).as_posix()]=entry[1].relative_to(ROOT).as_posix()
            duplicates.append((path,entry[1]))
    print(json.dumps(dict(originals=len(forms),redundant_files=len(duplicates),aliases=aliases),indent=2))
    if not args.apply:return
    for source,target in canonical.values():
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copyfile(source,target)
        if digest(source)!=digest(target):raise ValueError('Target differs')
    # Commit all DB pointers before deleting any duplicate bytes.
    with engine().begin() as db:
        for sha,paths in targets.items():
            db.execute(text('UPDATE form SET raw_path=:raw,pdf_path=:pdf WHERE sha256=:sha'),dict(sha=sha,**paths))
        for row in db.execute(text('SELECT id,report FROM analysis_run')).mappings():
            db.execute(text('UPDATE analysis_run SET report=CAST(:report AS jsonb) WHERE id=:id'),dict(id=row['id'],report=json.dumps(replace_paths(row['report'],aliases))))
    for path in (ROOT/'data').rglob('*.json'):
        old=json.loads(path.read_text(encoding='utf-8'))
        new=replace_paths(old,aliases)
        if new!=old:path.write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf-8')
    # Keep a durable relocation index for old provenance records/bookmarks.
    index=ROOT/'data/forms/storage-aliases.json'
    old=json.loads(index.read_text(encoding='utf-8')) if index.exists() else {}
    index.write_text(json.dumps({**old,**aliases},indent=2),encoding='utf-8')
    data_root=(ROOT/'data').resolve()
    for duplicate,target in duplicates:
        if not duplicate.resolve().is_relative_to(data_root) or not target.resolve().is_relative_to(data_root):raise ValueError('Path outside data workspace')
        if digest(duplicate)!=digest(target):raise ValueError('Duplicate changed during consolidation')
        duplicate.unlink()
    from api.storage import export_shared_form,export_procedure
    for form in forms:export_shared_form(form['sha256'])
    with engine().connect() as db:
        codes=list(db.execute(text('SELECT code FROM procedure WHERE active')).scalars())
    for code in codes:export_procedure(code)
    print('Consolidation complete; unique originals and historical versions preserved.')


if __name__=='__main__':main()
