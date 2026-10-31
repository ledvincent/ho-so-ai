"""Package the public procedure database and its source assets for teammates.

Stage the related repository assets first. Uses the configured DATABASE_URL and
the Compose db service on the same PostgreSQL server. No applicant/session tables
are permitted. A PostgreSQL snapshot keeps metadata and the dump consistent.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED

from sqlalchemy import text
from api.config import ROOT, engine

PUBLIC_TABLES = set('''alembic_version analysis_baseline analysis_run
attachment_observation catalog_batch embedding_cache embedding_space fact fee
form form_family form_field procedure procedure_analysis procedure_comparison
procedure_form procedure_profile procedure_profile_head rag_chunk rag_head
rag_item rag_member rag_release rag_source requirement requirement_form
search_text source_page submission_method'''.split())
ASSET_PREFIXES = ('data/_store/', 'data/archive/raw/', 'data/forms/',
                  'data/baselines/', 'data/procedures/', 'data/runs/')


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def referenced_assets(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == 'page_sha256' and isinstance(child, str) and len(child) == 64:
                page = ROOT/'data/_store/form-sources'/child
                if not page.is_file():
                    # Some landing sources are the original official PDF itself.
                    page = next((p for p in (ROOT/'data/forms/_objects'/child).glob('*')
                                 if p.is_file() and digest(p.read_bytes()) == child), None)
                if page is None:
                    raise ValueError('Missing archived official landing source: '+child)
                yield page.relative_to(ROOT).as_posix()
            yield from referenced_assets(child)
    elif isinstance(value, list):
        for child in value:
            yield from referenced_assets(child)
    elif isinstance(value, str) and value.startswith(ASSET_PREFIXES) and '\n' not in value:
        yield value


def main():
    assets = set()
    with engine().connect().execution_options(isolation_level='REPEATABLE READ') as db:
        db.execute(text('SET TRANSACTION READ ONLY'))
        tables = set(db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars())
        if tables != PUBLIC_TABLES:
            raise ValueError('Database schema changed; review the public table allowlist before exporting.')
        snapshot = db.execute(text('SELECT pg_export_snapshot()')).scalar_one()
        database = db.execute(text('SELECT current_database()')).scalar_one()
        for table in sorted(tables):
            for row in db.execute(text(f'SELECT to_jsonb(t) FROM "{table}" t')).scalars():
                assets.update(referenced_assets(row))
        codes = list(db.execute(text('SELECT code FROM procedure WHERE active ORDER BY code')).scalars())
        release = db.execute(text('''SELECT r.*, s.configuration FROM rag_head h
            JOIN rag_release r ON r.id=h.release_id JOIN embedding_space s ON s.id=r.space_id''')).mappings().one()
        items = db.execute(text('SELECT count(*) FROM rag_item WHERE release_id=:r'), {'r':release['id']}).scalar_one()
        missing = db.execute(text('SELECT count(*) FROM rag_item WHERE release_id=:r AND embedding IS NULL'), {'r':release['id']}).scalar_one()
        if release['status'] != 'published' or missing:
            raise ValueError('Serving search release is incomplete.')
        stale = db.execute(text('''SELECT count(*) FROM procedure p LEFT JOIN rag_member m
            ON m.code=p.code AND m.release_id=:r
            LEFT JOIN procedure_profile_head h ON h.snapshot_id=p.current_snapshot_id
            WHERE p.active AND (m.code IS NULL OR m.snapshot_id<>p.current_snapshot_id OR m.profile_id<>h.profile_id)'''), {'r':release['id']}).scalar_one()
        if stale:
            raise ValueError('Publish an index matching every active procedure before exporting.')
        migration = db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
        dump = subprocess.run(['docker','compose','exec','-T','db','pg_dump','-U','hoso',
            '-d',database,'--format=custom','--no-owner','--no-acl','--snapshot='+snapshot],
            cwd=ROOT, capture_output=True, check=True).stdout
    copies = json.loads((ROOT/'data/forms/official-copies.json').read_text(encoding='utf-8'))
    assets.update(referenced_assets(copies))
    tracked = set(subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0'))
    archived = {'procedure-db.dump': dump}
    repository = {}
    for name in sorted(assets):
        path = (ROOT/name).resolve()
        if not path.is_relative_to((ROOT/'data').resolve()) or not path.is_file():
            raise ValueError('Missing or invalid public source asset: '+name)
        if name in tracked:
            payload = subprocess.check_output(['git','show',':'+name], cwd=ROOT)
            local = path.read_bytes()
            if local != payload and local.replace(b'\r\n',b'\n') != payload:
                raise ValueError('Stage the current source asset before exporting: '+name)
            repository[name] = digest(payload)
        else:
            archived[name] = path.read_bytes()
    folder = ROOT/'data/bootstrap'
    folder.mkdir(exist_ok=True)
    archive = folder/'procedure-data.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED,compresslevel=9) as bundle:
        for name, payload in sorted(archived.items()):
            bundle.writestr(name,payload)
    config = release['configuration']
    manifest = dict(format_version=2, created_at=datetime.now(timezone.utc).isoformat(),
        archive=archive.name, archive_sha256=digest(archive.read_bytes()),
        database=dict(procedure_codes=codes,procedure_count=len(codes),release_id=str(release['id']),
                      index_items=items,migration=migration,min_similarity=release['min_similarity']),
        embedding_configuration=config,
        files={name:digest(payload) for name,payload in sorted(archived.items())},
        repository_files=repository,
        excluded=['credentials','.env','applicant data','local UI','Ollama model weights'])
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Packaged {len(codes)} procedures, {items} index items, {len(archived)-1} bundled assets and {len(repository)} repository assets; {archive.stat().st_size/1e6:.1f} MB.')


if __name__ == '__main__':
    main()
