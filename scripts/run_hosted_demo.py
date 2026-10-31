"""Run the protected jury Next/API pair on dedicated loopback ports.

The manager supplies a separately created HTTPS tunnel origin. This script never
creates a tunnel, restores producer data, copies secrets or starts paid requests.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', required=True)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--web-port', type=int, default=3030)
    parser.add_argument('--api-port', type=int, default=8030)
    parser.add_argument('--vincent-url', default='http://127.0.0.1:8001')
    parser.add_argument('--pid-file', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'api'))
    from hoso_api.local_auth.runtime import valid_auth_origin
    if not valid_auth_origin(args.origin, 'hosted-demo'):
        parser.error('An exact canonical public HTTPS origin is required.')
    producer = urlsplit(args.vincent_url)
    if (producer.scheme != 'http' or producer.hostname != '127.0.0.1' or
            producer.username or producer.password or producer.path or producer.query or producer.fragment):
        parser.error('Vincent must use a private loopback HTTP origin.')
    if not args.database.is_absolute() or not args.database.is_file():
        parser.error('Provision a new isolated jury database first.')
    if not (root / 'web/.next/BUILD_ID').is_file():
        parser.error('Run the production build before starting the hosted demo.')
    if args.web_port == args.api_port or not all(1024 <= port <= 65535 for port in (args.web_port, args.api_port)):
        parser.error('Distinct user ports are required.')
    for port in (args.web_port, args.api_port):
        with socket.socket() as check:
            try:
                check.bind(('127.0.0.1', port))
            except OSError:
                parser.error(f'Dedicated port {port} is occupied; existing listeners are never reused.')
    common = os.environ.copy()
    # The Next process receives no provider credential. Only the API launcher
    # reads the authorized key file directly into its own memory.
    for key in list(common):
        if key in {'OPENAI_API_KEY', 'ASSISTANT_API_KEY', 'CLERK_SECRET_KEY', 'CLERK_JWT_KEY'}:
            common.pop(key, None)
    common.update(HOSO_AUTH_PROVIDER='local', HOSO_DEPLOYMENT_MODE='hosted-demo',
        HOSO_PUBLIC_ORIGIN=args.origin, HOSO_LOCAL_DEMO_SEED='false',
        HOSO_API_URL=f'http://127.0.0.1:{args.api_port}', HOSO_VINCENT_API_URL=args.vincent_url,
        NEXT_TELEMETRY_DISABLED='1', NODE_ENV='production')
    web_env = {**common, 'OPENAI_API_KEY': '', 'ASSISTANT_API_KEY': '',
               'CLERK_SECRET_KEY': '', 'CLERK_JWT_KEY': ''}
    api_env = dict(common)
    if not args.key_file and os.environ.get('OPENAI_API_KEY'):
        api_env['OPENAI_API_KEY'] = os.environ['OPENAI_API_KEY']
    api_command = [sys.executable, str(root / 'api/scripts/run_hosted_checkpoint.py'),
        '--database', str(args.database), '--origin', args.origin, '--port', str(args.api_port)]
    if args.key_file:
        api_command += ['--key-file', str(args.key_file)]
    import shutil
    node = shutil.which('node')
    if not node:
        parser.error('Node is unavailable.')
    web_command = [node, str(root / 'web/node_modules/next/dist/bin/next'),
        'start', '--hostname', '127.0.0.1', '--port', str(args.web_port)]
    processes = []
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        for command, directory, environment in [(api_command, root / 'api', api_env), (web_command, root / 'web', web_env)]:
            processes.append(subprocess.Popen(command, cwd=directory, env=environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0))
        if args.pid_file:
            args.pid_file.parent.mkdir(parents=True, exist_ok=True)
            args.pid_file.write_text(json.dumps({'launcher': os.getpid(), 'api': processes[0].pid,
                'web': processes[1].pid, 'web_port': args.web_port, 'api_port': args.api_port}), encoding='utf-8')
        print('Protected loopback processes started; verify health/auth before sharing the link.', flush=True)
        while not stopping:
            if any(process.poll() is not None for process in processes):
                raise RuntimeError('A demo service exited. Both owned services will stop.')
            time.sleep(0.5)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == '__main__':
    main()
