"""Bounded ingestion agent. Source HTML is evidence, never executable instructions."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import uuid
import tempfile
import os
import sys
import logging
import threading
from contextlib import contextmanager
from email.message import Message
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import text as sql

from api.config import ROOT, engine
from api.db import ingest
from api.documents import store_document, file_extension
from api.attachments import attach_download, attach_fallback, save_mapping
from api.parse import text, ParseError
from api.parse import parse as parse_portal
from urllib.parse import parse_qs
from api.procedure_sources import PORTAL_HOSTS, is_portal_url, portal_identity

log = logging.getLogger(__name__)


@contextmanager
def heartbeat(url):
    stop = threading.Event()
    def pulse():
        while not stop.wait(30):
            log.info('Still processing %s (waiting on source, conversion or model)', url)
    thread = threading.Thread(target=pulse, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join()

HOST = 'dichvucong.bocongan.gov.vn'
PORTAL = 'https://vpcp.dichvucong.gov.vn/p/home/dvc-trang-chu.html'
VERSION = 'mps-analysis-1'


def validate_url(url):
    u = urlparse(url)
    if u.scheme != 'https' or u.hostname not in PORTAL_HOSTS | {HOST,'csdl.dichvucong.gov.vn'} or u.port not in (None,443) or u.username or u.password:
        raise ValueError('Expected an HTTPS link on a supported official government host')
    if not ((u.hostname == HOST and (u.path == '/bocongan/bothutuc/tthc' or u.path.startswith('/public_dir/'))) or
            is_portal_url(url) or
            (u.hostname == 'csdl.dichvucong.gov.vn' and u.path == '/web/jsp/download_file.jsp' and parse_qs(u.query).get('ma'))):
        raise ValueError('Unsupported official source path')


def save_bytes(raw, url, folder, filename=None):
    if folder != 'raw':
        return dict(url=url, **store_document(raw, url, filename), fetched_at=datetime.now(timezone.utc).isoformat())
    digest = hashlib.sha256(raw).hexdigest()
    target = ROOT / 'data/_store' / ('html' if folder=='raw' else 'documents') / digest
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return dict(url=url, sha256=digest, raw_path=target.relative_to(ROOT).as_posix(), fetched_at=datetime.now(timezone.utc).isoformat())


def fetch(url, folder, filename=None):
    import time
    validate_url(url)
    time.sleep(2)
    with httpx.Client(timeout=45, follow_redirects=False) as client:
        response = client.get(url)
        response.raise_for_status()
    if folder != 'raw' and response.headers.get('content-disposition'):
        header=Message();header['content-disposition']=response.headers['content-disposition']
        filename=header.get_filename() or filename
    return save_bytes(response.content, url, folder, filename)


def parse_ministry(raw, record):
    soup = BeautifulSoup(raw.decode('utf-8-sig'), 'html.parser')
    sections = {}
    for item in soup.select('.tthc-list-item'):
        heading, content = item.select_one('.item-title'), item.select_one('.tthc-list-item-detail')
        if heading and content:
            key = text(heading)
            if key in sections:
                raise ParseError('Duplicate section: ' + key)
            sections[key] = content
    code = text(sections.get('Mã thủ tục'))
    if not re.fullmatch(r'\d\.\d{6}',code):
        raise ParseError('Missing national code')
    required = ['Trình tự thực hiện','Cách thức thực hiện','Thời hạn giải quyết','Thành phần hồ sơ','Yêu cầu - điều kiện','Cơ quan thực hiện','Phí','Lệ Phí']
    if any(not text(sections.get(k)) for k in required):
        raise ParseError('Missing official section')
    title = soup.select_one('h4')
    if not title or not text(title):
        raise ParseError('Missing procedure title')
    issues = []
    # Explicit expiry is a blocker. Other legal-currency checks still require review.
    all_text = ' '.join(text(s) for s in sections.values())
    for year in re.findall(r'(?:đến hết|hết ngày|áp dụng đến)[^.;]{0,60}?(20\d{2})', all_text, re.I):
        if int(year) < datetime.now(timezone.utc).year:
            issues.append('Source contains an expired applicability date: ' + year)
    links = {}
    for a in soup.select('a[href]'):
        url = urljoin(record['url'],a['href'])
        if urlparse(url).path.startswith('/public_dir/'):
            validate_url(url)
            links[url] = dict(url=url,label=text(a.parent))
    if not links:
        issues.append('No downloadable official form')
    p = dict(code=code,name=text(title),source_url=record['url'],fetched_at=record['fetched_at'],
        sha256=record['sha256'],parser_version=VERSION,status='parsed',issues=[],facts=[],requirements=[],methods=[],fees=[],forms=list(links.values()))
    for kind, heading in [('steps','Trình tự thực hiện'),('agency','Cơ quan thực hiện'),('conditions','Yêu cầu - điều kiện')]:
        p['facts'].append(dict(kind=kind,position=0,text_verbatim=text(sections[heading])))
    p['methods'].append(dict(position=0,method=text(sections['Cách thức thực hiện']),processing_time_verbatim=text(sections['Thời hạn giải quyết']),description_verbatim=text(sections['Cách thức thực hiện'])))
    for heading in ['Phí','Lệ Phí']:
        p['fees'].append(dict(method='See official submission methods',text_verbatim=heading+': '+text(sections[heading]),amount=None,currency=None,condition_verbatim=text(sections[heading]),condition_status='captured',detail_refs=[]))
    rows = sections['Thành phần hồ sơ'].select('tbody tr')
    for row in rows:
        cells = row.find_all('td',recursive=False)
        if len(cells) != 3:
            raise ParseError('Unsupported requirements table')
        counts = re.search(r'Bản chính:\s*(\d+)\s*Bản sao:\s*(\d+)',text(cells[2]))
        if not counts:
            raise ParseError('Unrecognized quantities')
        p['requirements'].append(dict(position=len(p['requirements']),group_heading='',text_verbatim=text(cells[0]),originals=int(counts[1]),copies=int(counts[2]),form_urls=[]))
    if not rows:
        raise ParseError('No structured requirement rows')
    p['document'] = dict(name=p['name'],sections=[dict(heading=k,text_verbatim=v.get_text('\n',strip=True)) for k,v in sections.items()])
    return p, {k:text(v) for k,v in sections.items()}, issues


def analyse_file(record, context='', use_model=True):
    import pymupdf
    source = ROOT / record['raw_path']
    raw = source.read_bytes()
    if raw.startswith(b'%PDF-'):
        pdf = source
    else:
        suffix = file_extension(raw)
        folder = ROOT / 'data/forms/_objects' / record['sha256']
        folder.mkdir(parents=True,exist_ok=True)
        pdf = folder/'blank.pdf'
        if not pdf.exists():
            temporary_root = ROOT/'tmp/conversion'
            temporary_root.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(dir=temporary_root) as temporary:
                temporary = Path(temporary)
                input_path = temporary/('original'+suffix)
                shutil.copyfile(source,input_path)
                command=['docker','run','--rm','--network','none','--cap-drop','ALL','--security-opt','no-new-privileges', '-v',str(temporary)+':/out']
                fonts=Path(os.getenv('FORM_FONT_DIR', 'C:/Windows/Fonts' if os.name=='nt' else '/usr/local/share/fonts'))
                if fonts.is_dir():
                    command.extend(['-v',str(fonts.resolve())+':/usr/local/share/fonts/host:ro'])
                command.extend(['hoso-doc-tools','/out/'+input_path.name])
                subprocess.run(command,check=True,capture_output=True,timeout=120)
                shutil.move(str(temporary/'original.pdf'),pdf)
    fields, pages = [], []
    with pymupdf.open(pdf) as document:
        if not len(document):
            raise ValueError('Empty document')
        for index,page in enumerate(document):
            pages.append(page.get_text())
            for line in [l for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines']]:
                value = ''.join(s['text'] for s in line['spans'])
                for match in re.finditer(r'[.\u2026_]{3,}',value):
                    # Approximate placement is explicitly draft; human review required.
                    rect = line['bbox']
                    width = rect[2]-rect[0]
                    bbox = [rect[0]+width*match.start()/max(1,len(value)),rect[1],rect[0]+width*match.end()/max(1,len(value)),rect[3]]
                    fields.append(dict(field_id=f'p{index+1}_f{len(fields)+1}',page=index+1,label=value[:match.start()].strip() or 'Unlabelled writable area',field_type='text',bbox=bbox,evidence=value,owner='unknown',requiredness='unknown'))
            for widget in page.widgets() or []:
                fields.append(dict(field_id=f'p{index+1}_w{widget.xref}',page=index+1,label=widget.field_label or widget.field_name,field_type='native_pdf',bbox=list(widget.rect),evidence=widget.field_name,owner='unknown',requiredness='unknown'))
        if not any(p.strip() for p in pages):
            raise ValueError('Scanned or unreadable form: OCR required')
    result = dict(pdf_path=pdf.relative_to(ROOT).as_posix(),fields=fields,pages=pages,issues=['Geometry-only draft; semantic model mapping pending'])
    if use_model:
        from api.field_mapping import map_form
        mapping = map_form(pdf, record['sha256'], context=context)
        result.update(fields=mapping['fields'], mapping_metadata={**mapping['metadata'], 'cache_path':mapping['cache_path'], 'input_fingerprint':mapping['input_fingerprint']},
                      issues=['Model field map requires human review']+mapping['result']['issues'])
    return result


def chunks(value, limit=1200):
    # Preserve source wording, with overlapping boundaries for long sections.
    for start in range(0,len(value),limit-150):
        yield value[start:start+limit]


def facts_available(parsed):
    if parsed['status']!='parsed' or not parsed.get('document'):
        return False
    # Filename fallback never overrides a positively identified older revision.
    requirements=' '.join(r['text_verbatim'] for r in parsed['requirements'])
    if 'NA5' in requirements:
        with engine().connect() as db:
            current=db.execute(sql("SELECT f.revision_reference FROM form_family ff JOIN form f ON f.sha256=ff.preferred_sha256 WHERE ff.code='NA5'")).scalar()
        cited=re.findall(r'\b\d{1,3}/20\d{2}/TT-BCA\b',requirements)
        if current and cited and current not in cited:
            return False
    return True


def read_primary(source, acquisition, allow_resolution=True):
    raw = (ROOT/source['raw_path']).read_bytes()
    if urlparse(source['url']).hostname not in PORTAL_HOSTS:
        parsed, sections, issues = parse_ministry(raw, source)
        return source, parsed, sections, issues
    code, name, resolved = portal_identity(raw, source['url'])
    if resolved:
        if not allow_resolution:
            raise ParseError('Saved replay must contain the complete resolved procedure page')
        original_url = source['url']
        source = fetch(resolved, 'raw')
        resolution = dict(url=resolved, mode='resolved_live', resolved_from=original_url,
                          sha256=source['sha256'], raw_path=source['raw_path'], fetched_at=source['fetched_at'])
        acquisition.append(resolution)
        raw = (ROOT/source['raw_path']).read_bytes()
        resolved_code, resolved_name, further_resolution = portal_identity(raw, resolved)
        if resolved_code != code or further_resolution:
            raise ParseError('Resolved page does not match the requested procedure identity')
        # Portal detail cards can retain an older spelling/title for the same
        # national code. Preserve both names; extract only the complete page.
        resolution.update(input_name=name,resolved_name=resolved_name,title_changed=name != resolved_name)
        name = resolved_name
    parsed = parse_portal(raw, code, source['url'], source['fetched_at'], name)
    return source, parsed, {s['heading']:s['text_verbatim'] for s in parsed['document']['sections']}, list(parsed['issues'])


def run(url, html=None, inbox=None, attachment_page=None, attachment_html=None,
        baseline=None, output_dir=None, fallback_html=None, fallback_attachment_html=None, prior=None):
    validate_url(url)
    from api.baseline import ensure,contract
    baseline=baseline or ensure()
    if baseline['id']!=contract()['id']:raise ValueError('Agent configuration changed after baseline was frozen')
    run_id = str(uuid.uuid4())
    report = dict(run_id=run_id,url=url,input_url=url,catalog_url=PORTAL,attachment_page=attachment_page,documents=[],issues=[],baseline_id=baseline['id'],acquisition=[])
    output_dir=Path(output_dir) if output_dir else ROOT/'data/runs'/run_id
    output_dir.mkdir(parents=True,exist_ok=True)
    prior=prior or {}
    with engine().begin() as db:
        db.execute(sql("INSERT INTO analysis_run(id,source_url,status,baseline_id) VALUES (:id,:url,'running',:baseline)"),dict(id=run_id,url=url,baseline=baseline['id']))
    try:
        log.info('Fetching procedure page: %s', url)
        try:
            source=save_bytes(Path(html).read_bytes(),url,'raw') if html else fetch(url,'raw')
            if html:source['fetched_at']=prior.get('fetched_at')  # unknown is not today's fetch
            report['acquisition'].append(dict(url=url,mode='saved_input' if html else 'live',sha256=source['sha256'],raw_path=source['raw_path'],fetched_at=source['fetched_at']))
            source,parsed,sections,issues=read_primary(source,report['acquisition'])
        except (httpx.HTTPError,ValueError) as exc:
            if not fallback_html:raise
            source=save_bytes(Path(fallback_html).read_bytes(),prior.get('source_url',url),'raw')
            source['fetched_at']=prior.get('fetched_at')
            if not source['fetched_at']:raise ValueError('Saved replay needs its original retrieval timestamp')
            source,parsed,sections,issues=read_primary(source,report['acquisition'],allow_resolution=False)
            report['acquisition'].append(dict(url=url,mode='saved_replay',error=str(exc),sha256=source['sha256'],original_fetched_at=source['fetched_at']))
        url=source['url']
        report.update(url=url,code=parsed['code'],name=parsed['name'],primary_source=source,primary_forms=parsed['forms'])
        log.info('%s: source captured; %s linked forms', parsed['code'], len(parsed['forms']))
        sid,_ = ingest(parsed,'foreigner' if 'người nước ngoài' in parsed['name'].lower() else 'citizen',source['raw_path'],activate=False)
        report['issues'].extend(issues)
        attachments = parsed['forms']
        if attachment_page:
            try:
                secondary=save_bytes(Path(attachment_html).read_bytes(),attachment_page,'raw') if attachment_html else fetch(attachment_page,'raw')
                if attachment_html:secondary['fetched_at']=prior.get('analysis',{}).get('report',{}).get('attachment_source',{}).get('fetched_at')
                secondary_parsed,_,secondary_issues=parse_ministry((ROOT/secondary['raw_path']).read_bytes(),secondary)
                report['acquisition'].append(dict(url=attachment_page,mode='saved_input' if attachment_html else 'live',sha256=secondary['sha256']))
            except (httpx.HTTPError,ValueError) as exc:
                if not fallback_attachment_html:raise
                secondary=save_bytes(Path(fallback_attachment_html).read_bytes(),attachment_page,'raw')
                secondary['fetched_at']=prior.get('analysis',{}).get('report',{}).get('attachment_source',{}).get('fetched_at')
                secondary_parsed,_,secondary_issues=parse_ministry((ROOT/secondary['raw_path']).read_bytes(),secondary)
                report['acquisition'].append(dict(url=attachment_page,mode='saved_replay',error=str(exc),sha256=secondary['sha256'],original_fetched_at=secondary['fetched_at']))
            if secondary_parsed['code'] != parsed['code']:
                raise ValueError('Supplementary attachment page has a different procedure code')
            report['attachment_source'] = secondary
            report['attachment_document'] = secondary_parsed['document']
            report['issues'].extend(secondary_issues)
            report['form_association_policy'] = 'Filename fallback to preferred shared family version'
            # Try primary URLs too. A supplementary page must not hide a working
            # primary download or replace its exact version.
            attachments = list({a['url']:a for a in parsed['forms']+secondary_parsed['forms']}.values())
            with engine().begin() as db:
                for item in attachments:
                    db.execute(sql("INSERT INTO procedure_form(snapshot_id,source_url,label) VALUES (:sid,:url,:label) ON CONFLICT DO NOTHING"),dict(sid=sid,**item))
        for attachment in attachments:
            log.info('%s: downloading form %s', parsed['code'], attachment['url'])
            record = None
            try:
                manual = None
                if inbox:
                    mapping = json.loads((Path(inbox)/'manifest.json').read_text(encoding='utf-8'))
                    manual = mapping.get(attachment['url'])
                    if manual:
                        manual = (Path(inbox)/manual).resolve()
                        if not manual.is_relative_to(Path(inbox).resolve()):
                            raise ValueError('Inbox file escapes its directory')
                label=attachment.get('label','')
                filename=label if re.fullmatch(r'[^/\\]{1,100}\.(?:docx?|pdf)',label,re.I) else None
                record = save_bytes(manual.read_bytes(),attachment['url'],'forms',filename) if manual else fetch(attachment['url'],'forms',filename)
                # Preserve the successful download even if conversion/model fails.
                with engine().begin() as db:
                    attach_download(db,sid,run_id,record)
                report['acquisition'].append(dict(url=attachment['url'],mode='manual_input' if manual else 'live_download',sha256=record['sha256']))
                result = analyse_file(record, context=json.dumps(parsed['document'],ensure_ascii=False))
                save_mapping(record['sha256'],result)
                observed_codes = sorted(set(re.findall(r'\b(?:TK|CT|CC|DC|NA)\d{1,2}\b',' '.join(result['pages']),re.I)))
                with engine().begin() as db:
                    for page_number,page_text in enumerate(result['pages'],1):
                        for position,body in enumerate(chunks(page_text)):
                            db.execute(sql("""INSERT INTO rag_chunk(snapshot_id,form_sha256,section,position,text_verbatim,source_url,locator,fetched_at)
                                VALUES (:sid,:sha,:section,:pos,:body,:url,:locator,:date) ON CONFLICT DO NOTHING"""),dict(sid=sid,sha=record['sha256'],section='form:'+record['sha256'],pos=page_number*10000+position,body=body,url=record['url'],locator=f'page {page_number}',date=record['fetched_at']))
                report['documents'].append(dict(url=record['url'],sha256=record['sha256'],original=record['raw_path'],original_filename=record['original_filename'],pdf=result['pdf_path'],field_count=len(result['fields']),observed_form_codes=observed_codes,status='draft',mapping_metadata=result.get('mapping_metadata',{})))
            except (httpx.HTTPError,ValueError,subprocess.SubprocessError,FileNotFoundError) as exc:
                log.warning('%s: form unavailable or mapping failed: %s', parsed['code'], exc)
                report['issues'].append(f"Attachment failed {attachment['url']}: {exc}")
                if record:
                    report['documents'].append(dict(url=record['url'],sha256=record['sha256'],original=record['raw_path'],status='mapping_failed',observed_form_codes=[],error=str(exc)))
                else:
                    report['acquisition'].append(dict(url=attachment['url'],mode='download_failed',error=str(exc)))
                    with engine().begin() as db:
                        db.execute(sql("""INSERT INTO attachment_observation(run_id,snapshot_id,source_url,fetched_at,status,error)
                            VALUES (:run,:sid,:url,now(),'failed',:error)"""),dict(run=run_id,sid=sid,url=attachment['url'],error=str(exc)))
        expected_codes = {c.upper() for c in re.findall(r'\b(?:TK|CT|CC|DC|NA)\d{1,2}\b',' '.join(r['text_verbatim'] for r in parsed['requirements']),re.I)}
        downloaded_codes = {c.upper() for d in report['documents'] for c in d['observed_form_codes']}
        if expected_codes-downloaded_codes:
            report['issues'].append('Required form codes not found in downloaded files: '+', '.join(sorted(expected_codes-downloaded_codes)))
        with engine().begin() as db:
            for form in parsed['forms']:
                family = re.fullmatch(r'([A-Z]+\d+)\.docx?',form['label'],re.I)
                if family:
                    preferred = db.execute(sql('SELECT preferred_sha256 FROM form_family WHERE code=:code'),dict(code=family[1].upper())).scalar()
                    if preferred:
                        attach_fallback(db,sid,form['url'],preferred,source['fetched_at'])
        # Run the same mapper on every distinct associated form, including a
        # cached original or a labelled filename fallback. Cache reuse is recorded.
        with engine().connect() as db:
            associated=[dict(r) for r in db.execute(sql('''SELECT DISTINCT ON(f.sha256) f.*,pf.source_url,pf.association_method,pf.fetched_at
                FROM procedure_form pf JOIN form f ON f.sha256=pf.form_sha256 WHERE pf.snapshot_id=:sid ORDER BY f.sha256'''),dict(sid=sid)).mappings()]
        analysed={d['sha256'] for d in report['documents'] if d['status']=='draft'}
        for form in associated:
            if form['sha256'] in analysed:continue
            record=dict(url=form['source_url'],sha256=form['sha256'],raw_path=form['raw_path'],fetched_at=str(form['fetched_at']))
            try:
                result=analyse_file(record,context=json.dumps(parsed['document'],ensure_ascii=False))
                save_mapping(form['sha256'],result)
                codes=sorted(set(re.findall(r'\b(?:TK|CT|CC|DC|NA)\d{1,2}\b',' '.join(result['pages']),re.I)))
                report['documents'].append(dict(url=form['source_url'],sha256=form['sha256'],original=form['raw_path'],pdf=result['pdf_path'],field_count=len(result['fields']),observed_form_codes=codes,status='draft',acquisition='stored_'+form['association_method'],mapping_metadata=result['mapping_metadata']))
            except (ValueError,httpx.HTTPError,subprocess.SubprocessError,FileNotFoundError) as exc:
                report['issues'].append('Stored form mapping failed '+form['sha256']+': '+str(exc))
        from api.profiles import extract
        profile=extract(parsed,sid,report,baseline,output_dir/'profile')
        with engine().begin() as db:
            pid=db.execute(sql('''INSERT INTO procedure_profile(snapshot_id,run_id,baseline_id,profile,sources,metadata,output_sha256)
                VALUES (:sid,:run,:baseline,CAST(:profile AS jsonb),CAST(:sources AS jsonb),CAST(:metadata AS jsonb),:sha) RETURNING id'''),
                dict(sid=sid,run=run_id,baseline=baseline['id'],profile=json.dumps(profile['profile']),sources=json.dumps(profile['sources']),
                     metadata=json.dumps({k:v for k,v in profile.items() if k not in ('profile','sources')}),sha=profile['output_sha256'])).scalar_one()
            db.execute(sql('''INSERT INTO procedure_profile_head(snapshot_id,profile_id) VALUES (:sid,:pid)
                ON CONFLICT(snapshot_id) DO UPDATE SET profile_id=excluded.profile_id'''),dict(sid=sid,pid=pid))
            # Replace only generated routing rows on the same snapshot. Old
            # profiles remain immutable in procedure_profile and batch artifacts.
            db.execute(sql('DELETE FROM search_text WHERE snapshot_id=:sid AND profile_id IS NOT NULL'),dict(sid=sid))
            for kind,key in [('alias','aliases'),('example_query','example_requests')]:
                for phrase in profile['profile'][key]:
                    db.execute(sql('''INSERT INTO search_text(snapshot_id,kind,lang,text,profile_id)
                        VALUES (:sid,:kind,:lang,:text,:pid) ON CONFLICT DO NOTHING'''),dict(sid=sid,kind=kind,lang=phrase['language'],text=phrase['text'],pid=pid))
        report['profile']=dict(profile_id=pid,path=(output_dir/'profile/profile.json').relative_to(ROOT).as_posix(),validation=profile['validation'],output_sha256=profile['output_sha256'])
        readiness = 'blocked' if report['issues'] else 'needs_review'
        facts_ready = facts_available(parsed)
        report['freshness']=dict(status='requires_recheck' if not facts_ready else 'source_captured_not_legally_reverified',procedure_updated_on=None)
        report['facts_ready'] = facts_ready
        summary = parsed['name']+' — '+sections.get('Lĩnh vực','')  # deterministic routing text
        with engine().begin() as db:
            db.execute(sql("""INSERT INTO procedure_analysis(snapshot_id,run_id,sections,summary,issues,readiness,facts_ready)
                VALUES (:sid,:run,CAST(:sections AS jsonb),:summary,CAST(:issues AS jsonb),:ready,:facts_ready)
                ON CONFLICT(snapshot_id) DO UPDATE SET run_id=excluded.run_id,sections=excluded.sections,summary=excluded.summary,issues=excluded.issues,readiness=excluded.readiness,facts_ready=excluded.facts_ready"""),dict(sid=sid,run=run_id,sections=json.dumps(sections),summary=summary,issues=json.dumps(report['issues']),ready=readiness,facts_ready=facts_ready))
            for section, value in sections.items():
                for position,body in enumerate(chunks(value)):
                    db.execute(sql("""INSERT INTO rag_chunk(snapshot_id,section,position,text_verbatim,source_url,locator,fetched_at)
                        VALUES (:sid,:section,:pos,:body,:url,:section,:date) ON CONFLICT DO NOTHING"""),dict(sid=sid,section=section,pos=position,body=body,url=url,date=source['fetched_at']))
            db.execute(sql("INSERT INTO search_text(snapshot_id,kind,lang,text) VALUES (:sid,'summary','vi',:summary) ON CONFLICT DO NOTHING"),dict(sid=sid,summary=summary))
            db.execute(sql('UPDATE procedure SET current_snapshot_id=:sid WHERE code=:code'),dict(sid=sid,code=parsed['code']))
        report['status'] = readiness
    except Exception as exc:
        report.update(status='failed',error=str(exc))
    except KeyboardInterrupt:
        report.update(status='failed',error='Interrupted by user',interrupted=True)
    with engine().begin() as db:
        db.execute(sql("UPDATE analysis_run SET completed_at=now(),status=:status,report=CAST(:report AS jsonb),procedure_code=:code,source_url=:url WHERE id=:id"),dict(id=run_id,status=report['status'],report=json.dumps(report),code=report.get('code') if report['status']!='failed' else None,url=report['url']))
    destination = ROOT/'data/_store/runs'/f'{run_id}.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (output_dir/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if report['status']!='failed':
        with engine().begin() as db:
            db.execute(sql('UPDATE procedure SET active=true WHERE code=:code'),dict(code=report['code']))
        from api.storage import export_procedure
        export_procedure(report['code'])
        log.info('%s: imported and exported (review status: %s)', report['code'], report['status'])
    if report.get('interrupted'):
        raise KeyboardInterrupt
    return report


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
    logging.getLogger('httpx').setLevel(logging.WARNING)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Ingest official procedure URLs; codes, names and linked forms are discovered automatically.')
    parser.add_argument('urls', nargs='*', metavar='URL')
    parser.add_argument('--urls-file', type=Path, help='UTF-8 text file containing one procedure URL per line')
    parser.add_argument('--resume', action='store_true', help='Skip URLs whose successful import is still the active profile; omit to refresh sources')
    parser.add_argument('--html',help='Saved HTML, with the URL retained as provenance')
    parser.add_argument('--inbox',help='Directory containing manifest.json mapping exact source URLs to local filenames')
    parser.add_argument('--attachment-page',help='Supplementary official page; procedure code must match; version review required')
    parser.add_argument('--attachment-html',help='Previously downloaded supplementary HTML')
    args = parser.parse_args()
    urls = list(args.urls)
    if args.urls_file:
        urls.extend(line.strip() for line in args.urls_file.read_text(encoding='utf-8-sig').splitlines()
                    if line.strip() and not line.lstrip().startswith('#'))
    urls = list(dict.fromkeys(urls))
    if not urls:
        parser.error('Provide a procedure URL or --urls-file')
    if len(urls) > 1 and any((args.html,args.inbox,args.attachment_page,args.attachment_html)):
        parser.error('Saved HTML, inbox and supplementary page options apply to one URL at a time')
    # Validate the whole list before starting database/model work.
    for url in urls:
        try:
            validate_url(url)
            u = urlparse(url)
            if not is_portal_url(url) and not (u.hostname == HOST and u.path == '/bocongan/bothutuc/tthc'):
                raise ValueError('Expected a procedure page, not a document download')
        except ValueError as exc:
            parser.error(str(exc))
    failed = False
    for number, url in enumerate(urls, 1):
        try:
            if args.resume:
                with engine().connect() as db:
                    existing = db.execute(sql('''SELECT p.code FROM procedure p
                        JOIN procedure_profile_head h ON h.snapshot_id=p.current_snapshot_id
                        JOIN procedure_profile pp ON pp.id=h.profile_id
                        JOIN analysis_run r ON r.id=pp.run_id
                        WHERE p.active AND r.status IN ('blocked','needs_review')
                        AND (r.source_url=:url OR r.report->>'input_url'=:url) LIMIT 1'''),dict(url=url)).scalar()
                if existing:
                    log.info('Procedure %s/%s: %s already imported; skipped', number, len(urls), existing)
                    continue
            log.info('Procedure %s/%s: %s', number, len(urls), url)
            with heartbeat(url):
                report = run(url,args.html,args.inbox,args.attachment_page,args.attachment_html)
        except Exception as exc:
            report = dict(input_url=url,status='failed',error=str(exc))
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
        failed = failed or report['status'] == 'failed'
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
