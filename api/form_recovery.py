"""Reuse inspected official copies without claiming they came from failed URLs."""
import hashlib
import json
from sqlalchemy import text
from api.config import ROOT


def verified_copies():
    path = ROOT / 'data/forms/official-copies.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else []


def choose_copy(code, attachment, copies=None):
    matches = []
    for item in verified_copies() if copies is None else copies:
        if item.get('candidate_only'):
            continue
        if not any(m['procedure_code'] == code and m['source_url'] == attachment['url']
                   and m['label'] == attachment.get('label', '') for m in item['matches']):
            continue
        record = item['record']
        path = (ROOT / record['raw_path']).resolve()
        if not path.is_relative_to((ROOT / 'data/forms').resolve()) or not path.is_file():
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']:
            matches.append(item)
    return matches[0] if len(matches) == 1 else None


def register_copy(db, item):
    r = item['record']
    metadata = {k: item.get(k) for k in ('family','summary','document_kind','page_url',
        'page_sha256','download_url','derivation','matching_basis','currency_note','candidate_only')}
    metadata.update(fetched_at=r['fetched_at'], inspected_official_copy=True,
                    current_applicability_verified=False)
    db.execute(text('''INSERT INTO form(sha256,raw_path,pdf_path,revision_reference,source_metadata,analysis_issues)
        VALUES (:sha,:raw,:pdf,:revision,CAST(:metadata AS jsonb),CAST(:issues AS jsonb))
        ON CONFLICT(sha256) DO UPDATE SET source_metadata=form.source_metadata || excluded.source_metadata,
        revision_reference=COALESCE(form.revision_reference,excluded.revision_reference),
        pdf_path=COALESCE(form.pdf_path,excluded.pdf_path)'''),
        dict(sha=r['sha256'],raw=r['raw_path'],pdf=item.get('pdf_path'),revision=item.get('revision'),
             metadata=json.dumps(metadata),issues=json.dumps(['Recovered official copy; field mapping and current applicability require review.'])))


def recover_official(db, sid, code, attachment, copies=None):
    item = choose_copy(code, attachment, copies)
    if not item:
        return dict(mode='official_copy_not_found')
    register_copy(db, item)
    r = item['record']
    count = db.execute(text('''UPDATE procedure_form SET form_sha256=:sha, fetched_at=:date,
        association_method='official_copy' WHERE snapshot_id=:sid AND source_url=:url
        AND (form_sha256 IS NULL OR association_method='filename_fallback'
             OR (association_method='official_copy' AND form_sha256=:previous))'''),
        dict(sha=r['sha256'],date=r['fetched_at'],sid=sid,url=attachment['url'],previous=item.get('replaces_sha256'))).rowcount
    return dict(mode='official_copy',sha256=r['sha256'],raw_path=r['raw_path'],
                download_url=item['download_url'],page_url=item['page_url'],
                association_updated=bool(count),current_applicability_verified=False)
