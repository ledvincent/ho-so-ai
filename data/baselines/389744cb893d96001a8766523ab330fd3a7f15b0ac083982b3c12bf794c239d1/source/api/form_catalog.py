"""Shared local form inventory and conservative recovery after a failed fetch."""
import hashlib
import json
import re
from pathlib import Path
from sqlalchemy import text
from api.config import ROOT, engine


def form_codes(label):
    return set(re.findall(r'(?<![A-Z0-9])([A-Z]{2,8}\d{1,4})(?![A-Z0-9])', label.upper()))


def inventory():
    with engine().connect() as db:
        forms=[dict(r) for r in db.execute(text('SELECT * FROM form ORDER BY sha256')).mappings()]
        observations=[dict(r) for r in db.execute(text("SELECT source_url,form_sha256,fetched_at FROM attachment_observation WHERE status IN ('downloaded','historical_download')")).mappings()]
        labels=[dict(r) for r in db.execute(text('SELECT form_sha256,label FROM procedure_form WHERE form_sha256 IS NOT NULL')).mappings()]
    for form in forms:
        sha=form['sha256']
        metadata=ROOT/'data/forms/_objects'/sha/'metadata.json'
        info=json.loads(metadata.read_text(encoding='utf-8')) if metadata.exists() else {}
        form['family']=(form.get('source_metadata') or {}).get('family') or info.get('family','unknown')
        form['labels']=sorted({r['label'] for r in labels if r['form_sha256']==sha})
        if form['family']=='unknown':
            codes=form_codes(' '.join(form['labels'])+' '+Path(form['raw_path']).stem)
            if len(codes)==1:form['family']=next(iter(codes))
        form['downloads']=[r for r in observations if r['form_sha256']==sha]
        # Only recorded original downloads establish an exact URL match.
        source=form.get('source_metadata') or {}
        if source.get('download_url') and source.get('fetched_at') and not source.get('derivation'):
            form['downloads'].append(dict(source_url=source['download_url'],fetched_at=source['fetched_at']))
        path=(ROOT/form['raw_path']).resolve()
        form['available']=(path.is_relative_to((ROOT/'data/forms').resolve()) and path.is_file()
                           and hashlib.sha256(path.read_bytes()).hexdigest()==sha)
    return forms


def select_local(url, label, forms):
    available=[f for f in forms if f['available']]
    exact=[f for f in available if any(d['source_url']==url for d in f['downloads'])]
    if len(exact)==1:
        form=exact[0]
        dates=[str(d['fetched_at']) for d in form['downloads'] if d['source_url']==url]
        return dict(mode='stored_exact_url',form=form,fetched_at=max(dates))
    if exact:
        return dict(mode='ambiguous',candidates=[f['sha256'] for f in exact])
    codes=form_codes(label)
    matches=[f for f in available if codes & form_codes(f['family'])]
    if len(matches)==1:
        return dict(mode='stored_family_candidate',form=matches[0],fetched_at=None)
    return dict(mode='ambiguous' if matches else 'not_found',candidates=[f['sha256'] for f in matches])


def recover_local(db, sid, attachment, forms):
    result=select_local(attachment['url'],attachment.get('label',''),forms)
    form=result.get('form')
    if form:
        # Never replace a positively downloaded association with an inference.
        updated=db.execute(text('''UPDATE procedure_form SET form_sha256=:sha,
            association_method=:method,fetched_at=:date WHERE snapshot_id=:sid AND source_url=:url
            AND (form_sha256 IS NULL OR (:exact AND association_method='filename_fallback'))'''),dict(sha=form['sha256'],sid=sid,url=attachment['url'],
            exact=result['mode']=='stored_exact_url',
            method='direct_download' if result['mode']=='stored_exact_url' else 'filename_fallback',
            date=result['fetched_at'])).rowcount
        return dict(mode=result['mode'],sha256=form['sha256'],raw_path=form['raw_path'],
                    original_fetched_at=result['fetched_at'],association_updated=bool(updated),
                    stored_sources=sorted({d['source_url'] for d in form['downloads']}),
                    version_verified=False)
    return result


def export_catalog(forms=None):
    forms=inventory() if forms is None else forms
    folder=ROOT/'data/forms';folder.mkdir(parents=True,exist_ok=True)
    def cell(value):return str(value or 'Unknown').replace('|','\\|').replace('\n',' ')
    lines=['# Form index','',f'{len(forms)} stored versions across {len({f["family"] for f in forms})} family labels.',
           '', 'Generated from the shared form registry. Original files are hash-checked. '
           'A stored form or matching code does not establish current applicability or approval.',
           '', '| Form | Summary / document heading | Revision | Availability | Review | Files / sources |',
           '| --- | --- | --- | --- | --- | --- |']
    for form in sorted(forms,key=lambda f:(f['family'],f['sha256'])):
        summary=(form.get('source_metadata') or {}).get('summary') or '; '.join(form['labels']) or 'Stored blank document; title not yet identified.'
        if form.get('pdf_path') and not (form.get('source_metadata') or {}).get('summary'):
            import pymupdf
            pdf=(ROOT/form['pdf_path']).resolve()
            if pdf.is_relative_to(folder.resolve()) and pdf.is_file():
                with pymupdf.open(pdf) as document:
                    headings=[s.strip() for s in document[0].get_text().splitlines() if len(s.strip())>10
                              and s.strip().isupper() and not s.strip().startswith(('CỘNG HÒA','ĐỘC LẬP'))]
                    if headings:summary=' / '.join(headings[:3])
        # Legacy Word files often retain readable Unicode even when their old
        # PDF font encodings lose Vietnamese glyphs. This is a heading excerpt,
        # not a legal summary or an execution of the document's contents.
        if form['available'] and Path(form['raw_path']).suffix.lower()=='.doc' and not (form.get('source_metadata') or {}).get('summary'):
            raw=(ROOT/form['raw_path']).read_bytes().decode('utf-16le',errors='ignore')
            headings=[s.strip() for s in re.findall(r'[A-ZÀ-ỸĐ 0-9(),.\-]{15,}',raw)
                      if s.strip().startswith(('TỜ KHAI','ĐƠN ','PHIẾU ','APPLICATION '))]
            if headings:summary=' / '.join(headings[:2])
        links=[]
        if form['available']:
            path=Path(form['raw_path']).relative_to('data/forms').as_posix()
            links.append(f'[Original](<{path}>)')
        links.extend(f'[Source {i}]({url})' for i,url in enumerate(sorted({d['source_url'] for d in form['downloads']}),1))
        source=form.get('source_metadata') or {}
        if source.get('page_url'):links.append(f'[Official page]({source["page_url"]})')
        if source.get('derivation'):links.append('Extracted pages '+', '.join(map(str,source['derivation']['pages'])))
        lines.append('| '+' | '.join([cell(form['family'])+' · `'+form['sha256'][:12]+'`',cell(summary),
                     cell(form.get('revision_reference')), 'Verified bytes' if form['available'] else 'Missing/corrupt',
                     cell(form.get('review_status')), ' · '.join(links) or 'No source recorded'])+' |')
    (folder/'index.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    export_catalog()
