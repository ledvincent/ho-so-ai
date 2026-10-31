"""Exact download associations take precedence over inferred family matches."""
import json
from sqlalchemy import text
from api.config import engine


def attach_download(db, sid, run_id, record):
    db.execute(text('''INSERT INTO form(sha256,raw_path) VALUES (:sha256,:raw_path)
        ON CONFLICT(sha256) DO UPDATE SET raw_path=excluded.raw_path'''), record)
    db.execute(text('''UPDATE procedure_form SET form_sha256=:sha256,fetched_at=:fetched_at,
        association_method='direct_download' WHERE snapshot_id=:sid AND source_url=:url'''), {**record,'sid':sid})
    db.execute(text('''INSERT INTO attachment_observation
        (run_id,snapshot_id,source_url,original_filename,form_sha256,fetched_at,status)
        VALUES (:run,:sid,:url,:original_filename,:sha256,:fetched_at,'downloaded')'''),
        {**record,'run':run_id,'sid':sid,'original_filename':record.get('original_filename')})


def attach_fallback(db, sid, url, sha, observed_at):
    # A prior exact download also survives a later transient fetch failure.
    return db.execute(text('''UPDATE procedure_form SET form_sha256=:sha,fetched_at=:date,
        association_method='filename_fallback' WHERE snapshot_id=:sid AND source_url=:url
        AND (form_sha256 IS NULL OR association_method='filename_fallback')
        AND NOT EXISTS (SELECT 1 FROM attachment_observation o
            WHERE o.snapshot_id=:sid AND o.source_url=:url AND o.form_sha256 IS NOT NULL)'''),
        dict(sha=sha,date=observed_at,sid=sid,url=url)).rowcount


def save_mapping(sha, result):
    """Atomically replace draft fields only; never downgrade an approved mapping."""
    with engine().begin() as db:
        current = db.execute(text('SELECT review_status FROM form WHERE sha256=:sha FOR UPDATE'),dict(sha=sha)).scalar_one()
        if current == 'reviewed':
            return
        db.execute(text('''UPDATE form SET pdf_path=:pdf,fields_json=CAST(:fields AS jsonb),
            analysis_issues=CAST(:issues AS jsonb),mapping_metadata=CAST(:meta AS jsonb)
            WHERE sha256=:sha'''), dict(sha=sha,pdf=result['pdf_path'],fields=json.dumps(result['fields']),
            issues=json.dumps(result['issues']),meta=json.dumps(result.get('mapping_metadata',{}))))
        db.execute(text('DELETE FROM form_field WHERE form_sha256=:sha'),dict(sha=sha))
        for field in result['fields']:
            placement = (field.get('placements') or [dict(page=field.get('page',1),bbox=field.get('bbox',[]))])[0]
            db.execute(text('''INSERT INTO form_field(form_sha256,field_id,page,label,field_type,bbox,evidence,owner,requiredness)
                VALUES (:sha,:id,:page,:label,:type,CAST(:bbox AS jsonb),:evidence,:owner,:requiredness)'''),
                dict(sha=sha,id=field.get('id',field.get('field_id')),page=placement['page'],bbox=json.dumps(placement['bbox']),
                     label=field['label'],type=field.get('type',field.get('field_type')),evidence=field.get('evidence',''),
                     owner=field.get('owner','unknown'),requiredness='required' if field.get('required') else 'optional'))
