"""Human-readable exports of the active procedure dataset."""
import json
import shutil
import yaml
import hashlib
import re
from pathlib import Path
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from api.config import ROOT, engine
from api.db import get_procedure
from api.documents import store_document


def write_json(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(jsonable_encoder(value),ensure_ascii=False,indent=2),encoding='utf-8')


def export_index():
    rows = []
    selected = yaml.safe_load((ROOT/'candidates.yaml').read_text(encoding='utf-8'))['procedures']
    for item in selected:
        code = item['code']
        path = ROOT/'data/procedures'/code/'procedure.json'
        if not path.exists():
            continue
        p = json.loads(path.read_text(encoding='utf-8'))
        refs = json.loads((path.parent/'forms.json').read_text(encoding='utf-8')) if (path.parent/'forms.json').exists() else []
        links = ' · '.join(f"[Original]({f['original'].removeprefix('data/')}) · [Fields]({f['fields'].removeprefix('data/')})" for f in {r['sha256']:r for r in refs}.values())
        rows.append(f"| [{code}](procedures/{code}/README.md) | {p['name']} | [Official procedure page]({p['source_url']}) | {links} |")
        readme = path.parent/'README.md'
        contents = readme.read_text(encoding='utf-8')
        contents = contents.replace('Source: '+p['source_url'], 'Source: [Open official procedure page]('+p['source_url']+')')
        readme.write_text(contents,encoding='utf-8')
    (ROOT/'data/README.md').write_text('# Active procedure data\n\nEach distinct downloaded document is stored once under forms/_objects/<hash>/. Procedure folders contain references only. Direct downloads retain the exact source version; inferred filename associations are labelled separately. Historical revisions remain available. Known stale procedure context is gated pending currency review.\n\n| Procedure | Official name | Government website | Shared form files |\n| --- | --- | --- | --- |\n'+'\n'.join(rows)+'\n\nFull captured procedure sections are in procedure.json → document_json, including every submission description. analysis.json is internal provenance, not user-facing assistant context. archive/ preserves earlier exploration. Procedure 1.002411 remains inactive.\n',encoding='utf-8')


def export_forms_index():
    versions = []
    na5=[]
    for metadata in sorted((ROOT/'data/forms/_objects').glob('*/metadata.json')):
        info = json.loads(metadata.read_text(encoding='utf-8'))
        version = metadata.parent.name
        original = Path(info['original']).name if info.get('original') else next(p for p in metadata.parent.iterdir() if p.suffix in ('.doc','.docx')).name
        row=f"| {info['family']} | {info.get('revision_reference') or 'Unverified revision'} | {'Preferred workflow template' if info.get('preferred') else 'Retained source version'} | [Original](_objects/{version}/{original}) · [Fields](_objects/{version}/fields.json) |"
        versions.append(row)
        if info['family']=='NA5':na5.append(row.replace('](_objects/','](../_objects/'))
    (ROOT/'data/forms/README.md').write_text('# Forms\n\nStart with [NA5](NA5/README.md): its workflow, review and distinct source versions are grouped there. `_objects/` is the shared content-addressed storage; do not copy its files into procedure folders. Same-name revisions remain separate and traceable.\n\n## All retained originals (including earlier exploration)\n\n| Family | Revision | Use | Files |\n| --- | --- | --- | --- |\n'+'\n'.join(versions)+'\n',encoding='utf-8')
    folder=ROOT/'data/forms/NA5';folder.mkdir(exist_ok=True)
    (folder/'README.md').write_text('# NA5\n\n[Current workflow fields](workflow.json) · [Source and dates](source.json) · [Review record](review.json)\n\nOne shared original per fingerprint. The 2015 originals are distinct downloaded versions, not redundant copies; a working procedure link must retain the exact bytes it served. The preferred 2026 template does not overwrite those associations. Model evidence and previous renderings are under `_objects/<hash>/`.\n\n| Family | Revision | Use | Files |\n| --- | --- | --- | --- |\n'+'\n'.join(na5)+'\n',encoding='utf-8')


def export_shared_form(sha):
    with engine().connect() as db:
        form = db.execute(text('SELECT * FROM form WHERE sha256=:sha'),dict(sha=sha)).mappings().one()
        fields = form['fields_json'] or [dict(f) for f in db.execute(text('SELECT * FROM form_field WHERE form_sha256=:sha ORDER BY page,field_id'),dict(sha=sha)).mappings()]
        preferred = db.execute(text('SELECT code FROM form_family WHERE preferred_sha256=:sha'),dict(sha=sha)).scalar()
        labels = list(db.execute(text('SELECT label FROM procedure_form WHERE form_sha256=:sha'),dict(sha=sha)).scalars())
        matches = re.findall(r'\b([A-Z]+\d+)\b',' '.join(labels),re.I)
        family = preferred or (matches[0].upper() if matches else 'unknown')
    folder = ROOT/'data/forms/_objects'/sha
    folder.mkdir(parents=True,exist_ok=True)
    source = ROOT/form['raw_path']
    stored = store_document(source.read_bytes(), (form.get('source_metadata') or {}).get('download_url',''), filename=source.name)
    original = ROOT/stored['raw_path']
    pdf = ROOT/form['pdf_path'] if form['pdf_path'] else None
    write_json(folder/'fields.json',fields)
    write_json(folder/'metadata.json',dict(sha256=sha,family=family,original=stored['raw_path'],preferred=bool(preferred),review_status=form['review_status'],revision_reference=form.get('revision_reference'),issued_on=form.get('issued_on'),effective_from=form.get('effective_from'),source_metadata=form.get('source_metadata'),mapping_metadata=form.get('mapping_metadata'),superseded_by_sha256=form.get('superseded_by_sha256')))
    export_forms_index()
    with engine().begin() as db:
        db.execute(text('UPDATE form SET raw_path=:raw WHERE sha256=:sha'),dict(raw=stored['raw_path'],sha=sha))
    return dict(sha256=sha,family=family,original=stored['raw_path'],pdf=pdf.relative_to(ROOT).as_posix() if pdf else None,fields=(folder/'fields.json').relative_to(ROOT).as_posix())


def export_procedure(code):
    p = get_procedure(code)
    if not p:
        return
    folder = ROOT/'data/procedures'/code
    folder.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/p['raw_path'],folder/'source.html')
    report = p['analysis']['report'] if p.get('analysis') else {}
    supplementary = report.get('attachment_source',{}).get('raw_path')
    if supplementary and (ROOT/supplementary).exists():
        shutil.copyfile(ROOT/supplementary,folder/'attachment-source.html')
    write_json(folder/'analysis.json',report)
    hashes = sorted({f['form_sha256'] for f in p['forms'] if f['form_sha256']})
    historical = {d['sha256'] for d in report.get('documents',[])}
    shared = {sha:export_shared_form(sha) for sha in set(hashes)|historical}
    refs = [{**shared[f['form_sha256']], 'source_url':f['source_url'], 'source_label':f['label'], 'association_method':f['association_method']} for f in p['forms'] if f['form_sha256']]
    write_json(folder/'forms.json',refs)
    p['shared_forms'] = refs
    write_json(folder/'procedure.json',p)
    if p.get('structured_profile'):
        write_json(folder/'profile.json',p['structured_profile'])
    # Remove only known convenience copies after comparing their content to the
    # shared store. Unknown/user-edited files are left untouched.
    legacy = (folder/'forms').resolve()
    assert legacy.is_relative_to((ROOT/'data/procedures').resolve())
    if legacy.exists():
        candidates = [(ROOT/r[k]) for r in shared.values() for k in ('original','pdf','fields') if r[k]]
        for old in legacy.iterdir():
            if old.is_file() and any(old.read_bytes()==target.read_bytes() for target in candidates):
                old.unlink()
        if not any(legacy.iterdir()):
            legacy.rmdir()
    links = '\n'.join(f"- [Shared {r['family']} original](../../{r['original'].removeprefix('data/')}) · [Draft fields](../../{r['fields'].removeprefix('data/')}) · {r['association_method']} · [download source]({r['source_url']})" for r in refs)
    profile_link=f"\n\nStructured profile and citations: [profile.json](profile.json). Baseline: `{p['structured_profile']['baseline_id']}`. Generated routing phrases are separate from sourced facts." if p.get('structured_profile') else ''
    (folder/'README.md').write_text(f"# {code}: {p['name']}\n\nSource: [Official procedure page]({p['source_url']})\n\nFull captured procedure: [procedure.json](procedure.json). Every visible section and submission description is retained. Form placements remain draft.{profile_link}\n\nShared form references: [forms.json](forms.json)\n\n{links}\n\nInternal provenance: [analysis.json](analysis.json). Original snapshots: source.html and attachment-source.html.\n",encoding='utf-8')
    export_index()
