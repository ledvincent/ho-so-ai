"""Database regression checks; all fixture rows are rolled back."""
import uuid
from sqlalchemy import text
from api.config import engine
from api.attachments import attach_download,attach_fallback


def main():
    with engine().connect() as db:
        transaction=db.begin()
        try:
            code='9.999999'
            db.execute(text("INSERT INTO procedure(code,audience) VALUES (:code,'foreigner')"),dict(code=code))
            sid=db.execute(text("""INSERT INTO source_page(procedure_code,source_url,sha256,fetched_at,raw_path,parser_version,name,status)
                VALUES (:code,'https://example.invalid/procedure',:sha,now(),'fixture','test','fixture','parsed') RETURNING id"""),dict(code=code,sha='f'*64)).scalar_one()
            run=str(uuid.uuid4())
            db.execute(text("INSERT INTO analysis_run(id,source_url,status) VALUES (:id,'https://example.invalid/procedure','running')"),dict(id=run))
            url='https://example.invalid/NA5.doc'
            db.execute(text("INSERT INTO procedure_form(snapshot_id,source_url,label) VALUES (:sid,:url,'NA5.doc')"),dict(sid=sid,url=url))
            for sha in ('1'*64,'2'*64):
                attach_download(db,sid,run,dict(sha256=sha,raw_path='fixture/'+sha+'.doc',url=url,original_filename='NA5.doc',fetched_at='2026-10-31T00:00:00Z'))
                assert attach_fallback(db,sid,url,'1'*64,'2026-10-31T00:00:00Z')==0
                row=db.execute(text('SELECT form_sha256,association_method FROM procedure_form WHERE snapshot_id=:sid'),dict(sid=sid)).one()
                assert row.form_sha256==sha and row.association_method=='direct_download'
            assert db.execute(text('SELECT count(DISTINCT form_sha256) FROM attachment_observation WHERE snapshot_id=:sid'),dict(sid=sid)).scalar_one()==2
            # A failed re-fetch doesn't destroy the last successful observation.
            assert attach_fallback(db,sid,url,'1'*64,'2026-11-01T00:00:00Z')==0
            other='https://example.invalid/broken/NA5.doc'
            db.execute(text("INSERT INTO procedure_form(snapshot_id,source_url,label) VALUES (:sid,:url,'NA5.doc')"),dict(sid=sid,url=other))
            assert attach_fallback(db,sid,other,'1'*64,'2026-10-31T00:00:00Z')==1
            print('PASS: exact download survives fallback and model failure; changed bytes retain distinct observations; broken link fallback works.')
        finally:
            transaction.rollback()


if __name__=='__main__':main()
