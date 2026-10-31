"""Read-only integration smoke; --live-assistant makes one paid model request.

Uses the real ASGI app, database and retrieval service. Never approves a template,
mocks a provider, saves applicant data, or prints configuration secrets/tokens.
"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import text

from api.config import ROOT, engine
from api.main import app


QUESTION = "How long does procedure 1.001146 take to process? Please answer in English."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-assistant', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'output/frontend-handoff-smoke.json')
    args = parser.parse_args()

    def git(*arguments):
        return subprocess.check_output(['git', *arguments], cwd=ROOT, text=True).strip()

    report = dict(created_at=datetime.now(timezone.utc).isoformat(),
                  transport='FastAPI TestClient / ASGI; not an HTTPS deployment test',
                  branch=git('branch', '--show-current'), base_sha=git('rev-parse', 'HEAD'),
                  working_tree_dirty=bool(git('status', '--porcelain')), checks=[])
    # Identify the source actually executed without hashing or opening .env.
    paths = sorted(set(ROOT.glob('api/**/*.py')) | {Path(__file__).resolve()})
    report['source_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in paths}

    def check(name, operation):
        try:
            detail = operation()
            report['checks'].append(dict(name=name, passed=True, detail=detail))
        except Exception as exc:
            # Exception text can contain a connection string. Record the type only.
            report['checks'].append(dict(name=name, passed=False, error_type=type(exc).__name__))
        print(name + ': ' + ('PASS' if report['checks'][-1]['passed'] else 'FAIL'), flush=True)

    with TestClient(app, raise_server_exceptions=False) as client:
        def endpoint(path):
            response = client.get(path)
            assert response.status_code == 200
            return response.json()

        check('health', lambda: endpoint('/health'))

        def setup():
            body = endpoint('/assistant/setup')
            assert body['index_ready'] and any(p['code'] == '1.001146' for p in body['procedures'])
            return body
        check('assistant_setup', setup)

        def release():
            with engine().connect() as db:
                version = db.execute(text('SELECT version_num FROM alembic_version')).scalar_one()
                row = dict(db.execute(text('''SELECT r.id, r.status, r.min_similarity,
                    s.configuration, (SELECT count(*) FROM rag_item i WHERE i.release_id=r.id) AS items
                    FROM rag_head h JOIN rag_release r ON r.id=h.release_id
                    JOIN embedding_space s ON s.id=r.space_id''')).mappings().one())
            return dict(migration=version, **row)
        check('serving_release', release)

        def search():
            response = client.post('/search', json={'query': '1.001146'})
            assert response.status_code == 200
            body = response.json()
            assert any(p['code'] == '1.001146' for p in body['results'])
            return body
        check('exact_procedure_search', search)

        def schema():
            body = endpoint('/documents/na5-provincial-stay-extension/schema')
            assert body['fields'] and body['procedure_code'] == '1.001146'
            return {**{key: body[key] for key in ('revision', 'review_status', 'fixed_values')},
                    'field_count': len(body['fields'])}
        check('na5_schema', schema)

        def preview():
            values = json.loads((ROOT/'tests/fixtures/na5-example.json').read_text(encoding='utf-8'))
            response = client.post('/documents/na5-provincial-stay-extension/preview', json={'values': values})
            assert response.status_code == 200 and response.headers['content-type'] == 'application/pdf'
            token = response.headers['X-Review-Token']
            with pymupdf.open(stream=response.content, filetype='pdf') as pdf:
                assert len(pdf) == 3 and 'ÉLODIE EXEMPLE' in pdf[0].get_text()
                pages = len(pdf)
            download = client.post('/documents/na5-provincial-stay-extension/download',
                                   json=dict(values=values, review_token=token, confirmed=True))
            reviewed = endpoint('/documents/na5-provincial-stay-extension/schema')['review_status'] == 'reviewed'
            assert download.status_code == (200 if reviewed else 409)
            return dict(preview_http=200, pages=pages, review_token_present=bool(token),
                        download_http=download.status_code, template_approved=reviewed,
                        mocked=False)
        check('na5_preview_and_real_download_gate', preview)

        def invalid_request():
            response = client.post('/assistant/chat', json={'message': 'x'})
            assert response.status_code == 422 and isinstance(response.json()['detail'], list)
            return dict(http_status=422)
        check('chat_input_validation', invalid_request)

        if args.live_assistant:
            def answer():
                request = dict(message=QUESTION, procedure_code='1.001146', history=[])
                response = client.post('/assistant/chat', json=request)
                body = response.json()
                # This fixed public question contains no applicant data. Omit signed state.
                report['live_example'] = dict(request=request, http_status=response.status_code,
                    response={key: value for key, value in body.items() if key != 'retrieval_state'})
                assert response.status_code == 200
                assert body['status'] == 'answered' and body['citations']
                assert body['procedure_code'] == '1.001146'
                assert all('[' + c['id'] + ']' in body['answer'] for c in body['citations'])
                return dict(http_status=200, citation_count=len(body['citations']),
                            note='Contract check only; review claim support and language separately.')
            check('live_assistant_answer', answer)
        else:
            report['live_assistant'] = 'not run; use --live-assistant to exercise the real provider'

    report['passed'] = all(c['passed'] for c in report['checks'])
    report['verified_at_base_sha'] = not report['working_tree_dirty']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('base_sha', 'working_tree_dirty', 'passed', 'checks')},
                     ensure_ascii=True, default=str))
    print('Report:', args.output)
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
