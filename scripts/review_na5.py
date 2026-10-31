"""Generate a fictional-data review packet, or record explicit human approval."""
import argparse
import hashlib
import json
from datetime import datetime,timezone
import pymupdf
from sqlalchemy import text
from api import na5
from api.config import ROOT,engine
from api.storage import write_json,export_shared_form

def family_example():
    values=json.loads((ROOT/'tests/fixtures/na5-example.json').read_text(encoding='utf-8'))
    for key in list(values):
        if key.startswith('organisation_'):del values[key]
    values.update(host_type='family',sponsor_kind='foreign_resident',sponsor_full_name='PERSONNE EXEMPLE',sponsor_birth_date='1988-03-21',sponsor_id_number='TEST987654',sponsor_id_issued_on='2020-01-15',sponsor_id_issuer='TEST AUTHORITY',sponsor_card_number='TEST-TRC-001',sponsor_card_issued_on='2025-04-01',sponsor_card_issuer='TEST IMMIGRATION OFFICE',sponsor_relationship='Brother',sponsor_address='789 Đường Ví Dụ, Hà Nội',sponsor_contact='relative@example.invalid')
    return values

def packet():
    mapping=na5.spec()
    review=pymupdf.open()
    for values in [json.loads((ROOT/'tests/fixtures/na5-example.json').read_text(encoding='utf-8')),family_example()]:
        raw=na5.render(values,draft=True)
        with pymupdf.open(stream=raw,filetype='pdf') as pdf:
            # Raster review pages avoid font-resource collisions when combining
            # two independently filled copies. Actual downloads remain vector PDFs.
            for source_page in pdf:
                page=review.new_page(width=source_page.rect.width,height=source_page.rect.height)
                page.insert_image(page.rect,pixmap=source_page.get_pixmap(matrix=pymupdf.Matrix(2,2)))
    target=ROOT/'output/pdf/na5-2026-review.pdf'
    target.parent.mkdir(parents=True,exist_ok=True)
    review.save(target)
    for i,page in enumerate(review):
        folder=ROOT/'tmp/pdfs/na5-review';folder.mkdir(parents=True,exist_ok=True)
        page.get_pixmap(matrix=pymupdf.Matrix(1.3,1.3)).save(folder/f'page-{i+1}.png')
    write_json(ROOT/'data/forms/NA5/review.json',dict(template_sha256=mapping['form_sha256'],spec_sha256=hashlib.sha256(na5.SPEC_PATH.read_bytes()).hexdigest(),packet_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),cases=['organisation','foreign family sponsor'],manual_areas=['certification/stamp','sponsor signature','applicant signature'],status='awaiting human review'))
    print(target)

def approve(reviewer):
    mapping=na5.spec()
    evidence=json.loads((ROOT/'data/forms/NA5/review.json').read_text(encoding='utf-8'))
    if evidence['spec_sha256']!=hashlib.sha256(na5.SPEC_PATH.read_bytes()).hexdigest():
        raise ValueError('Regenerate and review the packet after field-map changes')
    if evidence['packet_sha256']!=hashlib.sha256((ROOT/'output/pdf/na5-2026-review.pdf').read_bytes()).hexdigest():
        raise ValueError('Review packet changed; regenerate it')
    mapping.update(review_status='reviewed',reviewed_by=reviewer,reviewed_at=datetime.now(timezone.utc).isoformat())
    with engine().begin() as db:
        db.execute(text("UPDATE form SET review_status='reviewed',reviewed_by=:who,reviewed_at=:date WHERE sha256=:sha"),dict(who=reviewer,date=mapping['reviewed_at'],sha=mapping['form_sha256']))
        db.execute(text("UPDATE form_field SET review_status='reviewed' WHERE form_sha256=:sha"),dict(sha=mapping['form_sha256']))
    # The download gate reads this file. Keep it draft if the database update fails.
    write_json(na5.SPEC_PATH,mapping)
    export_shared_form(mapping['form_sha256'])
    print('Template review recorded. Preview values again before downloading.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--approve-by',help='Only after this person has reviewed the generated packet');args=p.parse_args()
    if args.approve_by:approve(args.approve_by)
    else:packet()

if __name__=='__main__':main()
