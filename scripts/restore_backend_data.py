"""Restore the checked-in public procedure snapshot into an empty local database.

Run after `docker compose up -d --wait`. Uses only Python's standard library and
the PostgreSQL tools in the Compose db service. Never reads or changes .env.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def verified_files(root=ROOT):
    folder = root / 'data/bootstrap'
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    archive = folder / 'procedure-data.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest['archive_sha256']:
        raise ValueError('Snapshot checksum mismatch; fetch the data bundle again.')
    with ZipFile(archive) as bundle:
        if len(bundle.namelist()) != len(set(bundle.namelist())) or set(bundle.namelist()) != set(manifest['files']):
            raise ValueError('Snapshot file inventory mismatch.')
        files = {}
        for name, expected in manifest['files'].items():
            if name != 'procedure-db.dump':
                path = (root / name).resolve()
                if not name.startswith(('data/_store/', 'data/archive/raw/', 'data/forms/',
                                        'data/baselines/', 'data/procedures/', 'data/runs/')) or not path.is_relative_to((root/'data').resolve()):
                    raise ValueError('Invalid snapshot asset path.')
            payload = bundle.read(name)
            if hashlib.sha256(payload).hexdigest() != expected:
                raise ValueError('Snapshot asset checksum mismatch.')
            files[name] = payload
    if 'procedure-db.dump' not in files:
        raise ValueError('Snapshot database dump is missing.')
    return manifest, files


def check_assets(root, files):
    for name, payload in files.items():
        if name == 'procedure-db.dump':
            continue
        path = root / name
        if path.exists() and (not path.is_file() or path.read_bytes() != payload):
            raise ValueError(f'Existing asset differs: {name}. Restore into a fresh checkout.')


def docker(*args, payload=None):
    result = subprocess.run(['docker', 'compose', 'exec', '-T', 'db', *args],
                            cwd=ROOT, input=payload, capture_output=True, check=True)
    return result.stdout.decode('utf-8').strip()


def restore(database, files, run=docker, root=ROOT):
    if not re.fullmatch(r'[a-z][a-z0-9_]{0,62}', database):
        raise ValueError('Use a database name containing lowercase letters, digits and underscores.')
    check_assets(root, files)
    exists = run('psql', '-U', 'hoso', '-d', 'postgres', '-At', '-c',
                 f"SELECT 1 FROM pg_database WHERE datname='{database}'") == '1'
    if exists:
        count = run('psql', '-U', 'hoso', '-d', database, '-At', '-c',
                    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname!='information_schema' "
                    "AND c.relkind IN ('r','p','v','m','S','f')")
        if int(count):
            raise ValueError(f'Database {database} is not empty; nothing was overwritten. '
                             'Use --database with a new name, then update DATABASE_URL.')
    else:
        run('createdb', '-U', 'hoso', database)
    for name, payload in files.items():
        if name != 'procedure-db.dump':
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(payload)
    run('pg_restore', '-U', 'hoso', '-d', database, '--no-owner', '--no-acl',
        '--exit-on-error', '--single-transaction', payload=files['procedure-db.dump'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='hoso')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    manifest, files = verified_files()
    if args.verify_only:
        print(f"Snapshot verified: {manifest['database']['procedure_count']} procedures; "
              f"{manifest['database']['index_items']} indexed items.")
        return
    restore(args.database, files)
    print(f"Restored {manifest['database']['procedure_count']} procedures and the published index.")
    print(f'DATABASE_URL=postgresql+psycopg://hoso:hoso_local@localhost:55432/{args.database}')
    print('Next: configure your model key and signing secrets in .env, pull bge-m3, '
          'then start api.main:app. See docs/kim-start-here.md.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f'Restore failed: {exc}', file=sys.stderr)
        raise SystemExit(1)
