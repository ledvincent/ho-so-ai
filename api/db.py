import json

from sqlalchemy import text

from api.config import engine


def ingest(parsed, audience, raw_path, activate=True):
    """Atomic snapshot activation. Prior facts survive; identical parses are no-ops."""
    p = parsed
    with engine().begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:code))"), p)
        db.execute(text("INSERT INTO procedure(code,audience) VALUES (:code,:audience) ON CONFLICT (code) DO NOTHING"), dict(code=p["code"], audience=audience))
        existing = db.execute(text("SELECT id FROM source_page WHERE procedure_code=:code AND sha256=:sha256 AND parser_version=:parser_version"), p).scalar()
        if existing:
            return existing, False
        sid = db.execute(text("""INSERT INTO source_page
            (procedure_code, source_url, sha256, fetched_at, raw_path, parser_version, name, status, issues,document_json)
            VALUES (:code,:source_url,:sha256,:fetched_at,:raw_path,:parser_version,:name,:status,CAST(:issues AS jsonb),CAST(:document AS jsonb)) RETURNING id"""),
            {**p, "raw_path": raw_path, "issues": json.dumps(p["issues"]),"document":json.dumps(p.get('document'))}).scalar_one()
        for table, key in [("fact", "facts"), ("submission_method", "methods"), ("fee", "fees")]:
            for row in p[key]:
                values = {**row, "snapshot_id": sid}
                if "detail_refs" in values:
                    values["detail_refs"] = json.dumps(values["detail_refs"])
                columns = list(values)
                binds = [f"CAST(:{c} AS jsonb)" if c == "detail_refs" else f":{c}" for c in columns]
                db.execute(text(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(binds)})"), values)
        form_ids = {}
        for form in p["forms"]:
            form_ids[form["url"]] = db.execute(text("INSERT INTO procedure_form(snapshot_id,source_url,label) VALUES (:sid,:url,:label) RETURNING id"), {**form, "sid": sid}).scalar_one()
        for req in p["requirements"]:
            rid = db.execute(text("""INSERT INTO requirement(snapshot_id,position,group_heading,text_verbatim,originals,copies)
                VALUES (:sid,:position,:group_heading,:text_verbatim,:originals,:copies) RETURNING id"""), {**req, "sid": sid}).scalar_one()
            for url in req["form_urls"]:
                db.execute(text("INSERT INTO requirement_form VALUES (:rid,:fid) ON CONFLICT DO NOTHING"), dict(rid=rid, fid=form_ids[url]))
        db.execute(text("INSERT INTO search_text(snapshot_id,kind,lang,text) VALUES (:sid,'name','vi',:name)"), dict(sid=sid, name=p["name"]))
        if activate:
            db.execute(text("UPDATE procedure SET current_snapshot_id=:sid WHERE code=:code"), dict(sid=sid, code=p["code"]))
        return sid, True


def get_procedure(code):
    with engine().connect() as db:
        row = db.execute(text("""SELECT p.code,p.audience,s.* FROM procedure p
            JOIN source_page s ON s.id=p.current_snapshot_id WHERE p.code=:code AND p.active"""), dict(code=code)).mappings().first()
        if not row:
            return None
        result = dict(row)
        sid = row["id"]
        analysis = db.execute(text("""SELECT a.readiness,a.facts_ready,a.issues,a.summary,r.report
            FROM procedure_analysis a JOIN analysis_run r ON r.id=a.run_id
            WHERE a.snapshot_id=:sid"""),dict(sid=sid)).mappings().first()
        result['analysis'] = dict(analysis) if analysis else None
        profile=db.execute(text('''SELECT pp.id,pp.run_id,pp.baseline_id,pp.profile,pp.sources,pp.metadata,pp.output_sha256
            FROM procedure_profile_head h JOIN procedure_profile pp ON pp.id=h.profile_id
            WHERE h.snapshot_id=:sid'''),dict(sid=sid)).mappings().first()
        result['structured_profile']=dict(profile) if profile else None
        provenance = {k: row[k] for k in ("source_url", "fetched_at", "sha256")}
        for table, key in [("fact", "facts"), ("requirement", "requirements"), ("submission_method", "methods"), ("fee", "fees")]:
            result[key] = [{**dict(r), **provenance} for r in db.execute(text(f"SELECT * FROM {table} WHERE snapshot_id=:sid ORDER BY id"), dict(sid=sid)).mappings()]
        result["forms"] = [dict(r) for r in db.execute(text("""SELECT pf.*, f.review_status,f.revision_reference,f.issued_on,f.effective_from,f.raw_path,f.pdf_path FROM procedure_form pf
            LEFT JOIN form f ON f.sha256=pf.form_sha256 WHERE pf.snapshot_id=:sid ORDER BY pf.id"""), dict(sid=sid)).mappings()]
        for form in result["forms"]:
            form["linked_from"] = provenance
            form['original_download_url'] = '/forms/'+form['form_sha256']+'/original' if form['form_sha256'] else None
        for req in result["requirements"]:
            req["form_ids"] = list(db.execute(text("SELECT procedure_form_id FROM requirement_form WHERE requirement_id=:id ORDER BY procedure_form_id"), req).scalars())
        return result
