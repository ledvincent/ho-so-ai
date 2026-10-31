"""Registered API acceptance: synthetic profiles, fresh local DB, no outbound calls."""
from copy import deepcopy

from fastapi.testclient import TestClient
import httpx
import pytest

from hoso_api.auth import AuthenticatedUser
from hoso_api.main import create_app
from hoso_api.settings import Settings

ORIGIN = 'http://127.0.0.1:3034'
FORM = 'a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751'
SCHEMA = '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3'


@pytest.fixture(autouse=True)
def no_outbound(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('PROFILE-01 must not call external services')
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', forbidden)


def details():
    return {'basics': {'full_legal_name': 'Synthetic Nguyễn', 'current_nationality': 'SYNTHETIC current'},
            'contact': {'phone_number': '+000000000'},
            'passport': {'document_number': 'SYNTHETIC-001'},
            'residence': {'temporary_address_in_vietnam': 'SYNTHETIC VN address'}}


def prefill(revision=1):
    return {'consent': True, 'applicant_confirmed': True, 'expected_revision': revision,
            'request_id': 'synthetic-generation-1', 'draft_revision': 3, 'procedure_code': '1.001146',
            'form_sha256': FORM, 'schema_version': SCHEMA, 'values': {'request_type': 'stay_extension'}}


class SyntheticVerifier:
    def verify(self, token):
        return AuthenticatedUser(subject='user_synthetic', session_id='session_synthetic')


class NoReadService:
    reads = 0
    def read_v2(self, user):
        self.reads += 1
        raise AssertionError('Unconsented requests must not read profile data')


@pytest.mark.parametrize('field,value', [('consent', False), ('consent', 1), ('consent', 'true'),
                                       ('applicant_confirmed', False), ('applicant_confirmed', 1), ('applicant_confirmed', None)])
def test_consent_rejected_before_profile_read(field, value):
    service = NoReadService()
    app = create_app(Settings(), session_verifier=SyntheticVerifier(), profile_service=service)
    body = prefill()
    body[field] = value
    with TestClient(app) as client:
        response = client.post('/v2/profile/prefill', json=body, headers={'Authorization': 'Bearer synthetic'})
        assert response.status_code == 422
        assert response.headers['cache-control'] == 'no-store'
        assert service.reads == 0


@pytest.mark.parametrize('method,path,payload', [('GET','/v2/profile', None), ('PUT','/v2/profile', {'expected_revision': 0, 'details': details()}),
                                               ('POST','/v2/profile/prefill', prefill())])
def test_all_new_routes_require_a_verified_session(method, path, payload):
    with TestClient(create_app(Settings())) as client:
        response = client.request(method, path, json=payload)
        assert response.status_code == 401
        assert response.headers['cache-control'] == 'no-store'


def test_real_local_v1_v2_roundtrip_isolation_prefill_and_logout(tmp_path):
    app = create_app(Settings(auth_provider='local', public_origin=ORIGIN, local_db_path=str(tmp_path / 'synthetic.sqlite'), local_demo_seed=True))
    with TestClient(app, client=('127.0.0.1', 50001)) as client:
        def login(username, password):
            response = client.post('/v1/auth/login', json={'username': username, 'password': password}, headers={'Origin': ORIGIN})
            assert response.status_code == 200
            return {'Authorization': 'Bearer ' + response.json()['session_token'], 'Origin': ORIGIN}
        a, b = login('admin', 'admin'), login('reviewer', 'reviewer-demo')
        assert client.get('/v2/profile', headers=a).status_code == 404
        saved = client.put('/v2/profile', json={'expected_revision': 0, 'details': details()}, headers=a)
        assert saved.status_code == 200
        rich = saved.json()
        assert rich['revision'] == 1
        assert client.get('/v2/profile', headers=b).status_code == 404
        v1 = client.get('/v1/profile', headers=a).json()
        assert set(v1['fields']) == {'full_name','date_of_birth','nationality','address','phone_number','email'}
        assert v1['profile_id'] == rich['profile_id']
        assert v1['fields']['full_name'] == rich['details']['basics']['full_legal_name']
        v1['fields']['full_name'] = 'Synthetic legacy edit'
        v1['fields']['nationality'] = 'SYNTHETIC ambiguous nationality'
        response = client.put('/v1/profile', json={'expected_revision': 1, 'fields': v1['fields']}, headers=a)
        assert response.status_code == 200 and response.json()['revision'] == 2
        after = client.get('/v2/profile', headers=a).json()
        assert after['details']['passport'] == rich['details']['passport']
        assert after['details']['basics']['current_nationality'] == 'SYNTHETIC current'
        assert after['legacy']['nationality'] == v1['fields']['nationality']
        assert client.put('/v2/profile', json={'expected_revision': 1, 'details': details()}, headers=a).status_code == 409
        assert client.post('/v2/profile/prefill', json=prefill(1), headers=a).status_code == 409
        proposal = client.post('/v2/profile/prefill', json=prefill(2), headers=a)
        assert proposal.status_code == 200
        assert proposal.json()['profile_revision'] == 2 and proposal.json()['review_status'] == 'draft'
        assert any(p['target_field'] == 'applicant_full_name' and p['value'] == 'SYNTHETIC LEGACY EDIT' for p in proposal.json()['proposals'])
        assert client.get('/v2/profile', headers=a).json() == after
        assert client.post('/v2/profile/prefill', json=prefill(2), headers=b).status_code == 404
        for extra in ('owner_subject', 'profile_id', 'legacy'):
            payload = {'expected_revision': 2, 'details': details(), extra: 'SYNTHETIC private marker'}
            denied = client.put('/v2/profile', json=payload, headers=a)
            assert denied.status_code == 422 and 'SYNTHETIC private marker' not in denied.text
        assert client.put('/v2/profile', json={'expected_revision': 2, 'details': details()}, headers={**a, 'Origin': 'https://foreign.invalid'}).status_code == 403
        assert client.post('/v2/profile/prefill', content=b'x' * 16385, headers={**a, 'Content-Type': 'application/json'}).status_code == 413
        assert client.post('/v1/auth/logout', json={}, headers=a).status_code == 200
        revoked = client.get('/v2/profile', headers=a)
        assert revoked.status_code == 401 and revoked.headers['cache-control'] == 'no-store'


def test_local_v2_boundaries_fail_closed_without_configuration():
    with TestClient(create_app(Settings(auth_provider='local')), client=('127.0.0.1', 50001)) as client:
        for path in ('/v2/profile', '/v2/profile/prefill'):
            response = client.get(path)
            assert response.status_code == 503 and response.headers['cache-control'] == 'no-store'


def test_mutation_validation_omits_private_input_and_unknown_keys():
    app = create_app(Settings(), session_verifier=SyntheticVerifier())
    invalid = details()
    invalid['passport']['document_number'] = 'SYNTHETIC-SECRET-' * 12
    invalid['SYNTHETIC-KEY-SECRET'] = 'SYNTHETIC-VALUE-SECRET'
    with TestClient(app) as client:
        response = client.put('/v2/profile', json={'expected_revision': 0, 'details': invalid}, headers={'Authorization': 'Bearer synthetic'})
        assert response.status_code == 422
        assert all(marker not in response.text for marker in ('SYNTHETIC-SECRET-', 'SYNTHETIC-KEY-SECRET', 'SYNTHETIC-VALUE-SECRET'))
