"""Private API for the explicit HTTPS jury demo; no weak seed or public bind."""
import argparse
import os
from pathlib import Path
import sys

from dotenv import dotenv_values
import uvicorn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--port', type=int, default=8030)
    parser.add_argument('--key-file', type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hoso_api.local_auth.runtime import valid_auth_origin
    from hoso_api.main import create_app
    from hoso_api.settings import Settings
    if not valid_auth_origin(args.origin, 'hosted-demo'):
        parser.error('An exact canonical public HTTPS origin is required.')
    if not args.database.is_absolute() or not args.database.is_file() or args.database.is_symlink():
        parser.error('Provision a fresh absolute jury database before startup.')
    if not 1024 <= args.port <= 65535:
        parser.error('A user port is required.')
    # Refuse old checkpoint databases with known weak-demo accounts.
    import sqlite3
    with sqlite3.connect(f'{args.database.as_uri()}?mode=ro', uri=True) as connection:
        users = connection.execute('SELECT username FROM local_auth_users').fetchall()
        if len(users) < 2 or any(row[0] in {'admin', 'reviewer'} for row in users):
            parser.error('Use a fresh jury database with nondefault accounts.')
    key = os.environ.get('OPENAI_API_KEY')
    if args.key_file:
        if not args.key_file.is_file() or args.key_file.is_symlink():
            parser.error('The authorized credential file is unavailable.')
        key = dotenv_values(args.key_file).get('OPENAI_API_KEY')
        if not key:
            parser.error('OPENAI_API_KEY is absent from the authorized file.')
    settings = Settings(auth_provider='local', deployment_mode='hosted-demo',
        public_origin=args.origin, local_api_host='127.0.0.1',
        local_db_path=str(args.database), local_demo_seed=False,
        demo_forms_enabled=True, cors_allowed_origins=(args.origin,),
        openai_api_key=key, assistant_model=os.environ.get('ASSISTANT_MODEL', 'gpt-4o-mini'))
    uvicorn.run(create_app(settings), host='127.0.0.1', port=args.port,
        access_log=False, proxy_headers=False, log_level='warning')


if __name__ == '__main__':
    main()
