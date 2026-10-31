"""Immutable retrieval releases and a resumable, leased embedding queue."""
import argparse
import hashlib
import json
import math
import os
import uuid
from functools import lru_cache

import httpx
from sqlalchemy import text
from api.config import engine

VERSION = 'rag-1'


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


@lru_cache(maxsize=1)
def client():
    return httpx.Client(timeout=httpx.Timeout(180, connect=5))


def endpoint():
    return os.getenv('RAG_EMBED_URL', 'http://localhost:11434').rstrip('/')


def space_config():
    model = os.getenv('EMBED_MODEL', 'bge-m3')
    response = client().get(endpoint() + '/api/tags')
    response.raise_for_status()
    models = response.json()['models']
    found = next((m for m in models if m['name'] in (model, model + ':latest')), None)
    if not found:
        raise RuntimeError('Embedding model is not installed; pull ' + model)
    return dict(model=found['name'], revision=found['digest'], dimensions=1024,
                input_version=VERSION, normalization='unit', provider='ollama')


def validate_vector(vector):
    if len(vector) != 1024 or not all(type(v) in (int, float) and math.isfinite(v) for v in vector):
        raise ValueError('Expected a finite 1024-dimensional vector')
    norm = math.sqrt(sum(v*v for v in vector))
    if norm == 0:
        raise ValueError('Zero embedding')
    return '[' + ','.join(str(v/norm) for v in vector) + ']'


def embed(values, config):
    # Verify the installed model digest before each batch, never mix model spaces.
    if space_config()['revision'] != config['revision']:
        raise RuntimeError('Embedding model revision changed; build a new release')
    response = client().post(endpoint() + '/api/embed', json={
        'model': config['model'], 'input': values, 'truncate': False, 'keep_alive': '15m'})
    response.raise_for_status()
    vectors = response.json()['embeddings']
    if len(vectors) != len(values):
        raise ValueError('Embedding batch length mismatch')
    return [validate_vector(v) for v in vectors]


def passages(body, limit=1400, overlap=150):
    """Exact source spans; prefer paragraph/sentence boundaries, never lose text."""
    start = 0
    while start < len(body):
        end = min(start + limit, len(body))
        if end < len(body):
            boundary = max(body.rfind('\n', start + limit//2, end), body.rfind('. ', start + limit//2, end))
            if boundary >= 0:
                end = boundary + 1
        yield start, end, body[start:end]
        if end == len(body):
            break
        start = max(start + 1, end - overlap)


def build(config=None):
    config = config or space_config()
    space = digest(canonical(config))
    with engine().begin() as db:
        # Prevent two builders publishing inconsistent membership snapshots.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('rag-build'))"))
        rows = list(db.execute(text('''SELECT p.code,s.id AS snapshot_id,s.name,
            pp.id AS profile_id,pp.output_sha256,pp.profile,pp.sources
            FROM procedure p JOIN source_page s ON s.id=p.current_snapshot_id
            JOIN procedure_profile_head h ON h.snapshot_id=s.id
            JOIN procedure_profile pp ON pp.id=h.profile_id AND pp.snapshot_id=s.id
            WHERE p.active AND s.status='parsed' ORDER BY p.code''')).mappings())
        if not rows:
            raise RuntimeError('No active profiles to index')
        fingerprint = digest(canonical([VERSION, space, [(r['code'],r['snapshot_id'],r['profile_id'],r['output_sha256']) for r in rows]]))
        existing = db.execute(text('SELECT id FROM rag_release WHERE fingerprint=:f'),dict(f=fingerprint)).scalar()
        if existing:
            return str(existing)
        release = str(uuid.uuid4())
        db.execute(text('INSERT INTO embedding_space(id,configuration) VALUES (:id,CAST(:c AS jsonb)) ON CONFLICT DO NOTHING'),dict(id=space,c=canonical(config)))
        db.execute(text('INSERT INTO rag_release(id,space_id,fingerprint) VALUES (:id,:space,:f)'),dict(id=release,space=space,f=fingerprint))
        def item(code,kind,body,source=None,start=None,end=None):
            hashed = digest(body)
            db.execute(text('''INSERT INTO embedding_cache(space_id,input_hash,input_text)
                VALUES (:space,:hash,:body) ON CONFLICT DO NOTHING'''),dict(space=space,hash=hashed,body=body))
            db.execute(text('''INSERT INTO rag_item(release_id,code,kind,source_id,input_hash,body,normalized,tsv,start_offset,end_offset)
                VALUES (:r,:code,:kind,:source,:hash,:body,lower(unaccent(:body)),to_tsvector('simple',unaccent(:body)),:start,:end)'''),
                dict(r=release,code=code,kind=kind,source=source,hash=hashed,body=body,start=start,end=end))
        for row in rows:
            db.execute(text('''INSERT INTO rag_member(release_id,code,snapshot_id,profile_id,name,profile)
                VALUES (:r,:code,:sid,:pid,:name,CAST(:profile AS jsonb))'''),dict(r=release,code=row['code'],sid=row['snapshot_id'],pid=row['profile_id'],name=row['name'],profile=canonical(row['profile'])))
            phrases = {row['name'], row['code']}
            for key in ('aliases','example_requests'):
                phrases.update(p['text'] for p in row['profile'][key])
            for key in ('purpose','outcome'):
                fact = row['profile'][key]
                if fact['status']=='supported' and fact['value']:
                    phrases.add(fact['value'])
            for phrase in sorted(phrases):
                item(row['code'],'routing',phrase)
            for form_code in sorted({f['form_code']['value'] for f in row['profile'].get('form_relationships',[]) if f['form_code']['status']=='supported' and f['form_code']['value']} - phrases):
                item(row['code'],'routing',form_code)
            for source in row['sources']:
                if source['kind']=='registry' or not source['text'].strip():
                    continue
                sid = 'src-' + digest(canonical([row['code'],source['source_id'],source['locator'],source['sha256']]))[:40]
                title = (row['name']+' — '+source['source_id']+' — '+source['locator'])[:500]
                db.execute(text('''INSERT INTO rag_source(release_id,code,id,kind,title,url,locator,body)
                    VALUES (:r,:code,:id,:kind,:title,:url,:locator,:body)'''),dict(r=release,code=row['code'],id=sid,kind=source['kind'],title=title,url=source['url'],locator=source['locator'],body=source['text']))
                for start,end,body in passages(source['text']):
                    item(row['code'],'evidence',body,sid,start,end)
        return release


def work(release, batch_size=8):
    processed = 0
    while True:
        token = str(uuid.uuid4())
        with engine().begin() as db:
            row = db.execute(text('''SELECT r.space_id,s.configuration FROM rag_release r
                JOIN embedding_space s ON s.id=r.space_id WHERE r.id=:r'''),dict(r=release)).mappings().one()
            jobs = list(db.execute(text('''SELECT c.input_hash,c.input_text FROM embedding_cache c
                WHERE c.space_id=:s AND c.embedding IS NULL AND c.attempts<5
                AND (c.retry_after IS NULL OR c.retry_after<=now())
                AND (c.lease_until IS NULL OR c.lease_until<now())
                AND EXISTS(SELECT 1 FROM rag_item i WHERE i.release_id=:r AND i.input_hash=c.input_hash)
                ORDER BY c.input_hash LIMIT :n FOR UPDATE SKIP LOCKED'''),dict(s=row['space_id'],r=release,n=batch_size)).mappings())
            for job in jobs:
                db.execute(text("UPDATE embedding_cache SET lease_until=now()+interval '10 minutes',lease_token=:t,attempts=attempts+1 WHERE space_id=:s AND input_hash=:h"),dict(t=token,s=row['space_id'],h=job['input_hash']))
        if not jobs:
            return processed
        try:
            vectors = embed([j['input_text'] for j in jobs], row['configuration'])
            with engine().begin() as db:
                for job,vector in zip(jobs,vectors):
                    db.execute(text('''UPDATE embedding_cache SET embedding=CAST(:v AS vector),error=NULL,
                        lease_until=NULL,lease_token=NULL,retry_after=NULL
                        WHERE space_id=:s AND input_hash=:h AND lease_token=:t'''),dict(v=vector,s=row['space_id'],h=job['input_hash'],t=token))
            processed += len(jobs)
            print(f'Embedded {processed} inputs',flush=True)
        except (httpx.HTTPError,ValueError,KeyError,RuntimeError) as exc:
            with engine().begin() as db:
                db.execute(text("UPDATE embedding_cache SET error=:e,lease_until=NULL,lease_token=NULL,retry_after=now()+interval '30 seconds' WHERE lease_token=:t"),dict(e=type(exc).__name__,t=token))
            raise


def publish(release, minimum=None):
    if minimum is not None and (not math.isfinite(minimum) or not 0<minimum<=1):
        raise ValueError('Invalid similarity threshold')
    with engine().begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext('rag-publish'))"))
        db.execute(text('SELECT id FROM rag_release WHERE id=:r FOR UPDATE'),dict(r=release)).one()
        pending = db.execute(text('''SELECT count(*) FROM rag_item i JOIN rag_release r ON r.id=i.release_id
            LEFT JOIN embedding_cache c ON c.space_id=r.space_id AND c.input_hash=i.input_hash
            WHERE i.release_id=:r AND c.embedding IS NULL'''),dict(r=release)).scalar_one()
        if pending:
            raise RuntimeError(f'{pending} items still need embeddings')
        db.execute(text('''UPDATE rag_item i SET embedding=c.embedding FROM rag_release r,embedding_cache c
            WHERE i.release_id=:r AND r.id=i.release_id AND c.space_id=r.space_id AND c.input_hash=i.input_hash'''),dict(r=release))
        db.execute(text("UPDATE rag_release SET status='published',min_similarity=:m WHERE id=:r"),dict(r=release,m=minimum))
        db.execute(text('''INSERT INTO rag_head(singleton,release_id) VALUES (true,:r)
            ON CONFLICT(singleton) DO UPDATE SET release_id=excluded.release_id'''),dict(r=release))
        db.execute(text('ANALYZE rag_item'))


def status():
    with engine().connect() as db:
        return [dict(r) for r in db.execute(text('''SELECT r.id,r.status,r.min_similarity,
            (h.release_id IS NOT NULL) AS serving,count(i.id) AS items,
            count(c.embedding) AS embedded,count(*) FILTER(WHERE c.error IS NOT NULL) AS failed
            FROM rag_release r LEFT JOIN rag_head h ON h.release_id=r.id
            LEFT JOIN rag_item i ON i.release_id=r.id
            LEFT JOIN embedding_cache c ON c.space_id=r.space_id AND c.input_hash=i.input_hash
            GROUP BY r.id,h.release_id ORDER BY r.created_at''')).mappings()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['build','work','publish','status'])
    parser.add_argument('--release')
    parser.add_argument('--minimum',type=float)
    args=parser.parse_args()
    if args.command=='build': print(build())
    elif args.command=='status': print(canonical(status()))
    elif not args.release: parser.error('--release is required')
    elif args.command=='work': work(args.release)
    else: publish(args.release,args.minimum)


if __name__=='__main__': main()
