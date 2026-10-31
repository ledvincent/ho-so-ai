"""Consumer tests against pinned Kim source, actual API/JWT/SQL, synthetic data.

Reuse producer test fixtures rather than clone her schema, storage or auth code.
Run with the source snapshot/api and son/access/src on PYTHONPATH (see README).
"""

import importlib.util
from pathlib import Path
import subprocess
import time

import hoso_api.profile
from hoso_api.auth import ClerkSessionVerifier
from hoso_api.profile import ProfileFields
from hoso_api.settings import Settings
import httpx
import pytest

from agent_access import AccessDenied, Authorization, Scope, Tool, ToolContext, ToolFailure, VerifiedIdentity
from agent_access.profile_adapter import PROFILE_READ_TOOL, ProfileReader

PRODUCER = "ae77fa8bd47d590a53d26690b687bcad80692a9b"
REPO = Path(__file__).resolve().parents[3]
API = Path(hoso_api.profile.__file__).resolve().parents[1]
fixture_path = API / "tests/test_profile_integration.py"
spec = importlib.util.spec_from_file_location("kim_profile_fixtures", fixture_path)
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)
signing = producer.signing
transactions = producer.transactions
service = producer.service
client = producer.client
no_external_http = producer.no_external_http


def token(signing, **overrides):
    return producer.credential(signing, **overrides)["Authorization"].removeprefix("Bearer ")


def context(*, owner=producer.A, session="profile_integration_synthetic_session", fields=frozenset({"full_name"})):
    return ToolContext(owner, "synthetic-conversation", "synthetic-procedure", fields, session)


def reader(client, signing):
    return ProfileReader(client=client, verifier=ClerkSessionVerifier(signing[1]))


def seed(client, signing):
    response = client.put("/v1/profile", headers=producer.credential(signing), json={
        "expected_revision": 0, "fields": {"full_name": "Synthetic Adapter A", "address": "Synthetic address"},
    })
    assert response.status_code == 200
    return response.json()


def assert_failure(code, operation):
    with pytest.raises(ToolFailure) as captured:
        operation()
    assert captured.value.code == code
    assert str(captured.value) == code


def test_actual_imports_and_fixtures_match_exact_published_producer():
    for relative in (
        "api/hoso_api/profile.py", "api/hoso_api/auth.py", "api/hoso_api/main.py",
        "api/hoso_api/portal/handlers.py", "api/hoso_api/portal/service.py",
        "api/hoso_api/portal/repository.py", "api/tests/test_profile_integration.py",
    ):
        expected = subprocess.run(["git", "show", f"{PRODUCER}:{relative}"], cwd=REPO,
                                  capture_output=True, check=True).stdout
        actual = (API.parent / relative).read_bytes()
        assert actual.replace(b"\r\n", b"\n") == expected.replace(b"\r\n", b"\n")


def test_real_route_returns_only_approved_field_and_keeps_null(client, signing):
    seed(client, signing)
    selected = reader(client, signing).read(token(signing), context(fields=frozenset({"full_name", "email"})))
    assert selected == {"full_name": "Synthetic Adapter A", "email": None}
    assert "profile_id" not in selected and "revision" not in selected and "address" not in selected


def test_real_route_404_does_not_create_profile(client, signing):
    assert_failure("PROFILE_NOT_FOUND", lambda: reader(client, signing).read(token(signing), context()))
    assert client.get("/v1/profile", headers=producer.credential(signing)).status_code == 404


def test_real_storage_failure_returns_sanitized_unavailable(client, signing, service, caplog):
    seed(client, signing)
    service.close()
    assert_failure("PROFILE_UNAVAILABLE", lambda: reader(client, signing).read(token(signing), context()))
    assert "Synthetic Adapter A" not in caplog.text


@pytest.mark.parametrize("overrides", [{"exp": 1}, {"iss": "https://wrong.invalid"}, {"sid": ""}, {"azp": "https://wrong.invalid"}])
def test_real_verifier_denies_bad_claims_before_profile_request(client, signing, transactions, overrides):
    with pytest.raises(AccessDenied):
        reader(client, signing).read(token(signing, **overrides), context())
    assert transactions.subjects == []


@pytest.mark.parametrize("ctx", [context(owner=producer.B), context(session="synthetic-another-login")])
def test_token_cannot_cross_account_or_login_binding(client, signing, transactions, ctx):
    with pytest.raises(AccessDenied):
        reader(client, signing).read(token(signing), ctx)
    assert transactions.subjects == []


def test_other_account_uses_actual_owner_route_not_owner_hint(client, signing):
    seed(client, signing)
    assert_failure("PROFILE_NOT_FOUND", lambda: reader(client, signing).read(
        token(signing, subject=producer.B), context(owner=producer.B)))


def test_invalid_fields_are_denied_before_storage(client, signing, transactions):
    with pytest.raises(AccessDenied):
        reader(client, signing).read(token(signing), context(fields=frozenset({"owner_subject"})))
    assert transactions.subjects == []


def test_no_new_verifier_or_identity_bypass_when_configuration_missing(client, signing):
    adapter = ProfileReader(client=client, verifier=ClerkSessionVerifier(Settings()))
    assert_failure("AUTH_UNAVAILABLE", lambda: adapter.read(token(signing), context()))


def test_read_does_not_change_revision_and_actual_write_conflict_remains_separate(client, signing):
    saved = seed(client, signing)
    adapter = reader(client, signing)
    adapter.read(token(signing), context())
    conflict = client.put("/v1/profile", headers=producer.credential(signing), json={
        "expected_revision": 0, "fields": {"full_name": "Synthetic must not overwrite"},
    })
    assert conflict.status_code == 409
    assert conflict.json() == {"detail": {"code": "PROFILE_REVISION_CONFLICT"}}
    adapter.read(token(signing), context())
    assert client.get("/v1/profile", headers=producer.credential(signing)).json() == saved


def test_core_gate_invokes_adapter_only_after_approval_and_preserves_404(client, signing, transactions):
    credential = token(signing)
    adapter = reader(client, signing)
    kim_verifier = ClerkSessionVerifier(signing[1])
    # Synthetic host bridge only; no claim that JWT verifies current revocation.
    def verify(value):
        user = kim_verifier.verify(value)
        return VerifiedIdentity(user.subject, user.session_id, time.monotonic() + 60)
    gate = Authorization(verifier=verify, tools={PROFILE_READ_TOOL: Tool(
        {"synthetic-procedure": frozenset(ProfileFields.model_fields)},
        lambda ctx: adapter.read(credential, ctx),  # synthetic token, test lifetime only
    )})
    conversation = gate.start(credential, procedure="synthetic-procedure")
    scope = Scope(PROFILE_READ_TOOL, frozenset({"full_name"}))
    request = gate.request(credential, conversation, scope=scope)
    with pytest.raises(AccessDenied):
        gate.dispatch(credential, conversation, request.request_id, scope=scope)
    assert transactions.subjects == []
    gate.decide(credential, conversation, request.request_id, approve=True)
    assert_failure("PROFILE_NOT_FOUND", lambda: gate.dispatch(credential, conversation, request.request_id, scope=scope))
    seed(client, signing)
    assert gate.dispatch(credential, conversation, request.request_id, scope=scope) == {"full_name": "Synthetic Adapter A"}
    gate.revoke(credential, conversation, request.request_id)
    previous_reads = len(transactions.subjects)
    with pytest.raises(AccessDenied):
        gate.dispatch(credential, conversation, request.request_id, scope=scope)
    assert len(transactions.subjects) == previous_reads


@pytest.mark.parametrize("kind", ["extra-field", "missing-field", "extra-envelope", "bad-type", "bad-revision", "missing-cache", "html", "redirect", "409", "timeout", "network", "huge", "malformed"])
def test_protocol_or_transport_failure_never_returns_private_values(signing, kind):
    calls = []
    payload = {"profile_id": "synthetic-id", "revision": 1,
               "fields": ProfileFields(full_name="Synthetic private marker").model_dump()}
    headers = {"cache-control": "no-store"}
    if kind == "extra-field": payload["fields"]["owner"] = "Synthetic private marker"
    if kind == "missing-field": del payload["fields"]["email"]
    if kind == "extra-envelope": payload["owner"] = "Synthetic private marker"
    if kind == "bad-type": payload["fields"]["full_name"] = ["Synthetic private marker"]
    if kind == "bad-revision": payload["revision"] = True
    if kind == "missing-cache": headers = {}
    def handle(request):
        calls.append(request)
        assert request.method == "GET" and request.url.path == "/v1/profile"
        assert not request.url.query and request.content == b""
        assert set(request.headers).isdisjoint({"x-owner-subject", "x-user-id"})
        if kind == "timeout": raise httpx.ReadTimeout("Synthetic private marker")
        if kind == "network": raise httpx.ConnectError("Synthetic private marker")
        if kind == "redirect": return httpx.Response(307, headers={"location": "https://wrong.invalid"})
        if kind == "html": return httpx.Response(200, text="Synthetic private marker", headers=headers)
        if kind == "malformed": return httpx.Response(200, content=b"{", headers={**headers, "content-type": "application/json"})
        if kind == "huge": return httpx.Response(200, content=b" " * 20_000, headers={**headers, "content-type": "application/json"})
        return httpx.Response(409 if kind == "409" else 200, json=payload, headers=headers)
    with httpx.Client(base_url="https://synthetic-api.invalid", transport=httpx.MockTransport(handle), follow_redirects=True) as client:
        adapter = reader(client, signing)
        code = "PROFILE_UNAVAILABLE" if kind in {"timeout", "network"} else "PROFILE_RESPONSE_INVALID"
        assert_failure(code, lambda: adapter.read(token(signing), context()))
    assert len(calls) == 1  # No redirects, retries, creation or writes.
