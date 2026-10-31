"""Create two fictional users in a NEW database; secrets never go to stdout."""
import argparse
import getpass
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys


def private_file(path: Path):
    if not path.is_absolute() or path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('An absolute private credential output path is required.')
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        account = subprocess.run(['whoami'], check=True, capture_output=True, text=True).stdout.strip()
        subprocess.run(['icacls', str(path.parent), '/inheritance:r', '/grant:r',
                        f'{account}:(OI)(CI)(F)', '*S-1-5-18:(OI)(CI)(F)'], check=True, capture_output=True)
    else:
        path.parent.chmod(0o700)
    # Reserve exclusively, restrict access before writing any credential bytes.
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        if os.name == 'nt':
            subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', f'{account}:(F)',
                            '*S-1-5-18:(F)'], check=True, capture_output=True)
        return os.fdopen(descriptor, 'w', encoding='utf-8')
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--credentials-file', type=Path,
                        help='Generate random passwords into this exclusive owner-readable private file.')
    parser.add_argument('--usernames', nargs=2, default=['jury-orchid', 'jury-lotus'])
    args = parser.parse_args()
    if not args.database.is_absolute() or args.database.exists() or '.runtime' not in args.database.parts:
        parser.error('An absolute NEW database path inside private .runtime is required.')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from hoso_api.local_auth.store import LocalAuthStore, normalized_username
    try:
        usernames = [normalized_username(value) for value in args.usernames]
    except Exception:
        parser.error('Use two valid fictional usernames.')
    if len(set(usernames)) != 2 or set(usernames) & {'admin', 'reviewer'}:
        parser.error('Two distinct nondefault usernames are required.')
    output = None
    try:
        if args.credentials_file:
            # Prevent accidentally placing credentials among tracked source files.
            if '.runtime' not in args.credentials_file.parts:
                parser.error('Credential output must be inside a private ignored .runtime directory.')
            output = private_file(args.credentials_file)
            accounts = [{'username': name, 'password': secrets.token_urlsafe(24)} for name in usernames]
        else:
            accounts = []
            for name in usernames:
                password = getpass.getpass(f'Password for {name} (12+ characters): ')
                if len(password) < 12 or password != getpass.getpass('Repeat password: '):
                    parser.error('Passwords must match and contain at least 12 characters.')
                accounts.append({'username': name, 'password': password})
        # Exclusive reservation prevents a race into an existing account database;
        # private parent permissions also protect SQLite journal files.
        with private_file(args.database):
            pass
        store = LocalAuthStore(args.database)
        try:
            for account in accounts:
                store.create_user(account['username'], account['password'])
            if output:
                json.dump({'accounts': accounts, 'fictional_demo_only': True}, output, indent=2)
                output.flush()
        finally:
            store.close()
    finally:
        if output:
            output.close()
    print('Created two fictional jury accounts. Credentials were not logged.')


if __name__ == '__main__':
    main()
