"""Install the verified-source 2026 NA5 and a manually curated, draft field map."""
import hashlib
import json
import re
from datetime import datetime,timezone
import pymupdf
from sqlalchemy import text
from api.config import ROOT,engine
from api.storage import export_shared_form,export_procedure,write_json

def dot_runs(page):
    runs=[]
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines',[]):
            chars=[c for span in line['spans'] for c in span['chars']]
            for match in re.finditer(r'[.\u2026]{3,}',''.join(c['c'] for c in chars)):
                boxes=[pymupdf.Rect(c['bbox']) for c in chars[match.start():match.end()]]
                runs.append([min(b.x0 for b in boxes),min(b.y0 for b in boxes),max(b.x1 for b in boxes),max(b.y1 for b in boxes)])
    return runs

def build_spec(source,pdf_path):
    fields=[]
    with pymupdf.open(ROOT/pdf_path) as pdf:
        runs=[dot_runs(pdf[i]) for i in range(2)]
        assert [len(r) for r in runs]==[30,27], 'Template geometry changed'
        boxes=[sorted([list(d['rect']) for d in pdf[i].get_drawings() if 8<=d['rect'].width<=10 and 8<=d['rect'].height<=10],key=lambda b:b[0]) for i in range(2)]
    def add(key,label,page,indices,group='Applicant',kind='text',required=True,when=None,**extra):
        if isinstance(indices,int): indices=[indices]
        field=dict(id=key,label=label,type=kind,required=required,group=group,owner=group.lower(),max_length=100,placements=[dict(page=page,bbox=runs[page-1][i]) for i in indices])
        field.update(extra)
        if when: field['when']=when
        fields.append(field)
    add('applicant_full_name','Full name (capital letters)',1,0)
    fields.append(dict(id='sex',label='Sex as recorded on the form',type='choice',options=['male','female'],required=True,group='Applicant',owner='applicant',placements=[dict(page=1,bbox=boxes[0][0])],marks={v:dict(page=1,bbox=b) for v,b in zip(['male','female'],boxes[0])}))
    add('birth_date','Date of birth',1,[1,2,3],kind='date')
    add('birth_nationality','Nationality at birth',1,4)
    add('current_nationality','Current nationality',1,5)
    add('occupation','Occupation / position',1,6)
    add('passport_number','Passport / travel document number',1,7,max_length=25)
    add('passport_type','Passport / travel document type',1,8,max_length=25)
    add('passport_issuer','Passport issuing authority',1,9,max_length=50)
    add('passport_expiry','Passport expiry date',1,[10,11,12],kind='date')
    add('entry_date','Most recent entry date',1,[13,14,15],kind='date')
    add('entry_port','Entry border gate / port',1,16,max_length=30)
    add('entry_purpose','Purpose of entry',1,17)
    add('permitted_until','Currently permitted to stay until',1,[18,19,20],kind='date')
    add('residential_address','Temporary residential address in Vietnam',1,21)
    add('contact','Applicant telephone / email',1,22)
    fields.append(dict(id='host_type',label='Who sponsors this application?',type='choice',options=['organisation','family'],required=True,group='Sponsor',owner='sponsor',placements=[]))
    org={'host_type':'organisation'}
    add('organisation_name','Hosting organisation name',1,23,'Organisation',when=org)
    add('organisation_address','Hosting organisation address',1,24,'Organisation',when=org)
    add('organisation_contact','Hosting organisation telephone / email',1,25,'Organisation',when=org)
    family={'host_type':'family'}
    fields.append(dict(id='sponsor_kind',label='Family sponsor status',type='choice',options=['vietnamese_citizen','foreign_resident'],required=True,group='Family sponsor',owner='family sponsor',when=family,placements=[]))
    for args in [('sponsor_full_name','Family sponsor full name',1,26,'text'),('sponsor_birth_date','Family sponsor date of birth',1,[27,28,29],'date'),('sponsor_id_number','Sponsor identity card / passport number',2,0,'text'),('sponsor_id_issued_on','Sponsor identity document issue date',2,[1,2,3],'date'),('sponsor_id_issuer','Sponsor identity document issuing authority',2,4,'text'),('sponsor_relationship','Relationship to applicant',2,10,'text'),('sponsor_address','Sponsor address in Vietnam',2,11,'text'),('sponsor_contact','Sponsor telephone / email',2,12,'text')]:
        key,label,page,index,kind=args
        add(key,label,page,index,'Family sponsor',kind=kind,when=family)
    foreign={'host_type':'family','sponsor_kind':'foreign_resident'}
    add('sponsor_card_number','Sponsor permanent / temporary residence card number',2,5,'Family sponsor',when=foreign)
    add('sponsor_card_issued_on','Sponsor residence card issue date',2,[6,7,8],'Family sponsor',kind='date',when=foreign)
    add('sponsor_card_issuer','Sponsor residence card issuing authority',2,9,'Family sponsor',when=foreign)
    # Visa issuance fields are accounted for but deliberately inactive for a stay extension.
    fields.append(dict(id='visa_entries',label='Visa single/multiple entries (not used for this extension)',type='choice',options=['single','multiple'],required=False,inactive=True,group='Request',owner='applicant',placements=[dict(page=2,bbox=boxes[1][0])],marks={v:dict(page=2,bbox=b) for v,b in zip(['single','multiple'],boxes[1])}))
    add('visa_valid_until','Visa valid until (not used for this extension)',2,[13,14,15],'Request',kind='date',required=False,inactive=True)
    add('extension_until','Requested stay extension until',2,[16,17,18],'Request',kind='date')
    add('reason','Reason for extension',2,19,'Request',max_length=130)
    add('additional_statements','Additional statements',2,[20,21],'Request',required=False,multiline=True,max_length=240)
    add('place_signed','Place of signing',2,[22,26],'Signing',repeat=True,max_length=20)
    add('signed_on','Date of signing',2,[23,24,25],'Signing',kind='date')
    for key,label in [('certification','Certification, signature, title and stamp (where applicable)'),('sponsor_signature','Sponsor signature and full name'),('applicant_signature','Applicant signature and full name')]:
        fields.append(dict(id=key,label=label,type='manual',manual=True,required=False,owner='signatory',group='Signing',placements=[]))
    return dict(form_sha256=source['sha256'],revision_reference='70/2026/TT-BCA',issued_on='2026-05-25',effective_from='2026-07-01',review_status='draft',reviewed_by=None,reviewed_at=None,pdf_path=pdf_path,pdf_sha256=hashlib.sha256((ROOT/pdf_path).read_bytes()).hexdigest(),procedure_code='1.001146',fields=fields,notes='All three original pages including notes are preserved. Signatures/stamps remain manual. Date and checkbox positions are mapped separately. The English/Vietnamese photo-count discrepancy in the official notes is retained, not silently rewritten.')

def main():
    existing=ROOT/'data/forms/NA5/workflow.json'
    if existing.exists() and json.loads(existing.read_text(encoding='utf-8')).get('mapping_metadata'):
        raise ValueError('NA5 now uses model-derived fields. Use scripts.map_na5; the legacy geometry installer must not overwrite that mapping.')
    seed=ROOT/'tmp/na5-current-analysis.json'
    if not seed.exists():seed=ROOT/'data/forms/NA5/source.json'
    saved=json.loads(seed.read_text(encoding='utf-8'))
    source=saved['source']; analysis=saved['analysis']
    revision=dict(source_url='https://congan.cantho.gov.vn/thu-tuc-hanh-chinh/thutuc/gia-han-tam-tru-cho-nguoi-nuoc-ngoai-tai-viet-nam-3.html',download_url=source['url'],legal_source_url='https://congbao.chinhphu.vn/van-ban/thong-tu-so-70-2026-tt-bca-469801.htm',fetched_at=source['fetched_at'],published_on=None,updated_on=None,verified_on='2026-10-31')
    with engine().begin() as db:
        db.execute(text("INSERT INTO form(sha256,raw_path,pdf_path,revision_reference,issued_on,effective_from,source_metadata) VALUES (:sha,:raw,:pdf,'70/2026/TT-BCA','2026-05-25','2026-07-01',CAST(:meta AS jsonb)) ON CONFLICT(sha256) DO NOTHING"),dict(sha=source['sha256'],raw=source['raw_path'],pdf=analysis['pdf_path'],meta=json.dumps(revision)))
        db.execute(text("UPDATE form SET superseded_by_sha256=:sha WHERE sha256 IN (SELECT form_sha256 FROM procedure_form WHERE label ILIKE '%NA5%') AND sha256!=:sha"),dict(sha=source['sha256']))
        db.execute(text("UPDATE form_family SET preferred_sha256=:sha,selection_basis='Verified 2026 printed revision, official police download and Gazette effective date' WHERE code='NA5'"),dict(sha=source['sha256']))
        db.execute(text("UPDATE procedure_form SET form_sha256=:sha WHERE association_method='filename_fallback' AND snapshot_id IN (SELECT current_snapshot_id FROM procedure WHERE active)"),dict(sha=source['sha256']))
    shared=export_shared_form(source['sha256'])
    write_json(ROOT/'data/forms/NA5/source.json',dict(source={**source,'raw_path':shared['original']},analysis=dict(pdf_path=shared['pdf'])))
    mapping=build_spec(source,shared['pdf'])
    write_json(ROOT/'data/forms/NA5/workflow.json',mapping)
    with engine().begin() as db:
        db.execute(text('UPDATE form SET fields_json=CAST(:fields AS jsonb) WHERE sha256=:sha'),dict(fields=json.dumps(mapping['fields']),sha=source['sha256']))
        for field in mapping['fields']:
            box=field['placements'][0] if field['placements'] else dict(page=2,bbox=[])
            db.execute(text("INSERT INTO form_field(form_sha256,field_id,page,label,field_type,bbox,requiredness,owner,profile_key,evidence) VALUES (:sha,:id,:page,:label,:type,CAST(:bbox AS jsonb),:required,:owner,:profile,:evidence) ON CONFLICT DO NOTHING"),dict(sha=source['sha256'],id=field['id'],page=box['page'],label=field['label'],type=field['type'],bbox=json.dumps(box['bbox']),required='required' if field.get('required') else 'optional',owner=field['owner'],profile='applicant.'+field['id'] if field['group']=='Applicant' else None,evidence=json.dumps(field['placements'])))
        # A source retrieval date is not an official update date. Preserve unknowns.
        for row in db.execute(text('SELECT code,current_snapshot_id FROM procedure WHERE active')).mappings():
            db.execute(text("UPDATE procedure_analysis SET facts_ready=false WHERE snapshot_id=:id"),dict(id=row['current_snapshot_id']))
            analysis_row=db.execute(text('SELECT run_id FROM procedure_analysis WHERE snapshot_id=:id'),dict(id=row['current_snapshot_id'])).mappings().one()
            report=db.execute(text('SELECT report FROM analysis_run WHERE id=:id'),dict(id=analysis_row['run_id'])).scalar_one()
            report.update(facts_ready=False,freshness=dict(status='requires_recheck',reason='Primary snapshot references a superseded NA5 revision; 2026 form is now verified',form_revision='70/2026/TT-BCA',form_effective_from='2026-07-01',procedure_published_on=None,procedure_updated_on=None))
            db.execute(text('UPDATE analysis_run SET report=CAST(:report AS jsonb) WHERE id=:id'),dict(report=json.dumps(report),id=analysis_row['run_id']))
    for code in ['1.003326','1.001146','1.003342','1.000771']:
        export_procedure(code)
    print('Installed verified 2026 NA5 with',len(mapping['fields']),'logical field definitions; template remains draft. Old procedure facts require freshness recheck before RAG.')

if __name__=='__main__':main()
