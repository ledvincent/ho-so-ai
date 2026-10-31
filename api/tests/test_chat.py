"""Offline CHAT-01 tests: actual protected routes, synthetic JWTs, fake model only."""

from copy import deepcopy
from hashlib import sha256
import json
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import httpx
import jwt
import pytest

from hoso_api.chat.provider import AssistantInvalidOutput, AssistantTimeout, AssistantUnavailable, OpenAIChatProvider
from hoso_api.chat.workflow import ASSET_PATH, FIELDS, FIXED_VALUES, WORKFLOW, WORKFLOW_SHA256, active, editable, schema_response
from hoso_api.main import create_app
from hoso_api.settings import Settings


def proposal(field="applicant_full_name", value="Synthetic Nguyen", evidence=None):
    return {"ambiguous": False, "proposals": [{"field_id": field, "value": value, "evidence": evidence or value}]}


class FakeProvider:
    def __init__(self, output=None, error=None):
        self.output = output if output is not None else proposal()
        self.error = error
        self.calls = []

    def propose(self, field_metadata, message):
        self.calls.append((deepcopy(field_metadata), message))
        if self.error:
            raise self.error
        return deepcopy(self.output)


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Chat tests must not call a live model or external HTTP service.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked)


@pytest.fixture(scope="module")
def signing():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")
    return private, Settings(clerk_jwt_key=public, clerk_issuer="https://chat-synthetic.clerk.accounts.dev",
                             clerk_authorized_parties=("http://127.0.0.1:3015",))


def credentials(signing, subject="chat_synthetic_a"):
    now = int(time.time())
    token = jwt.encode({"sub": subject, "sid": "chat_synthetic_session", "iss": signing[1].clerk_issuer,
                        "azp": "http://127.0.0.1:3015", "iat": now - 10, "nbf": now - 10, "exp": now + 120},
                       signing[0], algorithm="RS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def client(signing, provider):
    with TestClient(create_app(signing[1], chat_provider=provider)) as actual:
        yield actual


def body(**updates):
    return {"request_id": "synthetic-request-1", "draft_revision": 3, "procedure_code": "1.001146",
            "intent": "form_answer", "message": "My full name is Synthetic Nguyen",
            "focus_field": "applicant_full_name", "values": dict(FIXED_VALUES), **updates}


def assert_private(response, status):
    assert response.status_code == status, response.text
    assert response.headers["cache-control"] == "no-store"
    return response


def test_schema_is_exact_pinned_vincent_workflow_and_remains_draft(client, signing):
    assert sha256(ASSET_PATH.read_bytes()).hexdigest() == WORKFLOW_SHA256
    response = assert_private(client.get("/v1/chat/schema", headers=credentials(signing)), 200).json()
    assert len(response["fields"]) == 43
    assert response["fields"] == json.loads(ASSET_PATH.read_bytes())["fields"]
    assert response["fixed_values"] == {"request_type": "stay_extension"}
    assert response["schema_version"] == WORKFLOW_SHA256
    assert response["review_status"] == "draft"
    response["fields"][0]["label"] = "Local mutation"
    assert schema_response()["fields"][0]["label"] == WORKFLOW["fields"][0]["label"]


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer not-a-valid-session"}])
@pytest.mark.parametrize("endpoint", ["schema", "assist"])
def test_schema_and_assist_require_authenticated_current_user(client, provider, headers, endpoint):
    response = client.get("/v1/chat/schema", headers=headers) if endpoint == "schema" else client.post("/v1/chat/assist", headers=headers, json=body())
    assert_private(response, 401)
    assert provider.calls == []


def test_validated_proposal_echoes_correlation_and_asks_one_backend_question(client, signing, provider):
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body()), 200).json()
    assert response == {
        "request_id": "synthetic-request-1", "draft_revision": 3, "procedure_code": "1.001146",
        "schema_version": WORKFLOW_SHA256, "status": "proposed",
        "assistant_text": "A proposed value is ready for your review. Which Sex applies: male or female?",
        "proposed_changes": [{"field_id": "applicant_full_name", "value": "Synthetic Nguyen"}],
        "next_field": "sex", "review_status": "draft",
    }
    assert response["assistant_text"].count("?") == 1
    assert len(provider.calls) == 1


def test_provider_gets_only_active_metadata_and_message_not_other_values(client, signing, provider):
    values = {**FIXED_VALUES, "passport_number": "SYNTHETIC-SECRET-NOT-SENT", "contact": "private@example.invalid"}
    assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(values=values)), 200)
    metadata, message = provider.calls[0]
    assert set(metadata) == {"id", "label", "type", "max_length", "multiline"}
    serialized = json.dumps(provider.calls)
    assert "SYNTHETIC-SECRET-NOT-SENT" not in serialized
    assert "private@example.invalid" not in serialized
    assert "chat_synthetic_a" not in serialized
    assert message == "My full name is Synthetic Nguyen"


def test_empty_message_requests_initial_question_without_provider(client, signing, provider):
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(message="", focus_field=None)), 200).json()
    assert response["status"] == "question"
    assert response["next_field"] == "applicant_full_name"
    assert response["proposed_changes"] == []
    assert response["assistant_text"].count("?") == 1
    assert provider.calls == []


@pytest.mark.parametrize("field", ["request_type", "certification", "sponsor_signature", "applicant_signature", "visa_entries", "organisation_name"])
def test_fixed_manual_and_inactive_focus_cannot_call_model_or_receive_patch(client, signing, provider, field):
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(focus_field=field)), 200).json()
    assert response["status"] == "needs_clarification"
    assert response["proposed_changes"] == []
    assert provider.calls == []


@pytest.mark.parametrize("output", [
    {"ambiguous": True, "proposals": []},
    {"ambiguous": True, "proposals": [{"field_id": "applicant_full_name", "value": "Synthetic Nguyen", "evidence": "Synthetic Nguyen"}]},
    {"ambiguous": False, "proposals": []},
])
def test_ambiguity_never_changes_values_and_returns_one_clarification(client, signing, provider, output):
    provider.output = output
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body()), 200).json()
    assert response["status"] == "needs_clarification"
    assert response["proposed_changes"] == []
    assert response["next_field"] == "applicant_full_name"
    assert response["assistant_text"].count("?") == 1


@pytest.mark.parametrize("output", [
    {"ambiguous": "false", "proposals": []},
    {"ambiguous": False, "proposals": [], "assistant_text": "Untrusted procedural prose"},
    proposal("sex", "male"),
    proposal(value="Invented value", evidence="Synthetic Nguyen"),
    proposal(evidence="Not found in the user message"),
    {"ambiguous": False, "proposals": [proposal()["proposals"][0], proposal("sex", "male")["proposals"][0]]},
])
def test_malformed_unfocused_ungrounded_and_multi_field_output_is_rejected(client, signing, provider, output):
    provider.output = output
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body()), 502)
    assert response.json() == {"detail": {"code": "ASSISTANT_INVALID_OUTPUT"}}
    assert "Invented value" not in response.text


@pytest.mark.parametrize("field,value", [("sex", "unknown"), ("birth_date", "2026-02-30"), ("birth_date", "10/11/2000"), ("applicant_full_name", "X" * 101)])
def test_choices_calendar_dates_formats_and_lengths_are_validated_after_model(client, signing, provider, field, value):
    provider.output = proposal(field, value)
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(focus_field=field, message=value)), 502)
    assert response.json()["detail"]["code"] == "ASSISTANT_INVALID_OUTPUT"


@pytest.mark.parametrize("field,value", [("sex", "male"), ("birth_date", "2000-11-10")])
def test_explicit_choice_and_complete_iso_date_can_be_proposed(client, signing, provider, field, value):
    provider.output = proposal(field, value)
    result = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(focus_field=field, message=value)), 200).json()
    assert result["proposed_changes"] == [{"field_id": field, "value": value}]


def test_choice_evidence_cannot_match_inside_a_different_option(client, signing, provider):
    provider.output = proposal("sex", "male", "female")
    assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(focus_field="sex", message="female")), 502)


@pytest.mark.parametrize("field,message", [("sex", "male or female"), ("birth_date", "2000-01-01 or 2001-01-01")])
def test_explicit_conflicting_choices_or_dates_clarify_without_model(client, signing, provider, field, message):
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(focus_field=field, message=message)), 200).json()
    assert response["status"] == "needs_clarification"
    assert response["proposed_changes"] == []
    assert response["assistant_text"].count("?") == 1
    assert provider.calls == []


def test_selector_change_only_proposes_selector_and_rejects_stale_branch_values(client, signing, provider):
    provider.output = proposal("host_type", "family")
    values = {**FIXED_VALUES, "host_type": "organisation", "organisation_name": "Synthetic Organisation"}
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(focus_field="host_type", message="family", values=values)), 200).json()
    assert response["proposed_changes"] == [{"field_id": "host_type", "value": "family"}]
    # The UI must clear the previous branch before the following request.
    stale = {**values, "host_type": "family"}
    assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(values=stale)), 422)
    assert len(provider.calls) == 1
    provider.output = proposal("sponsor_full_name", "Synthetic Nguyen")
    cleared = {**stale, "organisation_name": None}
    result = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(focus_field="sponsor_full_name", values=cleared)), 200).json()
    assert result["proposed_changes"][0]["field_id"] == "sponsor_full_name"


@pytest.mark.parametrize("values", [
    {"request_type": "visa_issuance"}, {"unknown": "Synthetic private value"},
    {"host_type": "family", "organisation_name": "Stale organisation"},
    {"host_type": "organisation", "sponsor_kind": "foreign_resident"},
    {"host_type": "family", "sponsor_kind": "vietnamese_citizen", "sponsor_card_number": "Stale card"},
    {"birth_date": "2026-02-30"}, {"sex": "other"}, {"applicant_full_name": 42},
])
def test_invalid_or_inactive_request_values_are_not_sent_to_provider(client, signing, provider, values):
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(values=values)), 422)
    assert "Synthetic private value" not in response.text
    assert provider.calls == []


@pytest.mark.parametrize("update", [{"request_id": "unsafe id"}, {"draft_revision": -1}, {"draft_revision": True}, {"message": "x" * 2001}, {"procedure_code": "1.004194"}, {"focus_field": "unknown"}])
def test_request_bounds_and_exact_workflow_are_enforced(client, signing, provider, update):
    assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(**update)), 422)
    assert provider.calls == []


def test_procedure_question_is_explicitly_unavailable_without_model_or_fake_citations(client, signing, provider):
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(intent="procedure_question", message="What documents are legally required?")), 503)
    assert response.json() == {"detail": {"code": "RETRIEVAL_UNAVAILABLE"}}
    assert provider.calls == []


@pytest.mark.parametrize("error,status,code", [(AssistantUnavailable(), 503, "ASSISTANT_UNAVAILABLE"), (AssistantTimeout(), 504, "ASSISTANT_TIMEOUT"), (AssistantInvalidOutput(), 502, "ASSISTANT_INVALID_OUTPUT"), (RuntimeError("synthetic-private-provider-details"), 503, "ASSISTANT_UNAVAILABLE")])
def test_provider_errors_are_stable_and_sanitized(client, signing, provider, error, status, code):
    provider.error = error
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body()), status)
    assert response.json() == {"detail": {"code": code}}
    assert "synthetic-private" not in response.text


def test_absent_provider_only_blocks_nonempty_model_answers(signing):
    with TestClient(create_app(signing[1])) as actual:
        assert_private(actual.post("/v1/chat/assist", headers=credentials(signing), json=body()), 503)
        assert_private(actual.post("/v1/chat/assist", headers=credentials(signing), json=body(message="")), 200)


def test_complete_required_active_draft_skips_model(client, signing, provider):
    values = dict(FIXED_VALUES)
    for field in WORKFLOW["fields"]:
        if field["required"] and editable(field, values):
            values[field["id"]] = field["options"][0] if field["type"] == "choice" else "2000-01-01" if field["type"] == "date" else "Synthetic"
    response = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(values=values, focus_field=None, message="")), 200).json()
    assert response["status"] == "complete"
    assert response["next_field"] is None
    assert response["proposed_changes"] == []
    assert provider.calls == []


def test_drafts_are_stateless_not_persisted_and_late_correlation_is_echoed(client, signing):
    class NoProfileAccess:
        def read(self, *args):
            raise AssertionError("Chat must not read the saved profile.")

        def write(self, *args):
            raise AssertionError("Chat must not write the saved profile.")

    client.app.state.profile_service = NoProfileAccess()
    first = assert_private(client.post("/v1/chat/assist", headers=credentials(signing), json=body(request_id="old-response", draft_revision=1)), 200).json()
    second = assert_private(client.post("/v1/chat/assist", headers=credentials(signing, "chat_synthetic_b"), json=body(request_id="current-response", draft_revision=9, message="", focus_field=None)), 200).json()
    assert (first["request_id"], first["draft_revision"]) == ("old-response", 1)
    assert (second["request_id"], second["draft_revision"]) == ("current-response", 9)
    assert second["next_field"] == "applicant_full_name"
    assert second["proposed_changes"] == []


def completion(output, *, refusal=None, finish="stop"):
    return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(output), "refusal": refusal}}]}


def test_openai_transport_sends_strict_bounded_minimal_request_without_store_or_retries(monkeypatch):
    calls = []
    client_options = []
    original_client = httpx.Client

    def capture_client(*args, **kwargs):
        client_options.append(kwargs)
        return original_client(*args, **kwargs)

    def handler(request):
        calls.append(json.loads(request.content))
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        return httpx.Response(200, json=completion(proposal()))

    monkeypatch.setattr(httpx, "Client", capture_client)
    transport = httpx.MockTransport(handler)
    provider = OpenAIChatProvider("synthetic-api-key-not-real", transport=transport)
    metadata = {key: FIELDS["applicant_full_name"][key] for key in ("id", "label", "type", "max_length", "multiline")}
    assert provider.propose(metadata, "Synthetic Nguyen") == proposal()
    assert len(calls) == 1
    request = calls[0]
    assert request["model"] == "gpt-4o-mini"
    assert request["store"] is False
    assert request["max_completion_tokens"] == 450
    assert request["response_format"]["json_schema"]["strict"] is True
    assert json.loads(request["messages"][1]["content"]) == {"field": metadata, "message": "Synthetic Nguyen"}
    assert client_options[0]["trust_env"] is False
    assert client_options[0]["timeout"].read == 15


@pytest.mark.parametrize("response", [
    {}, {"choices": []}, completion(proposal(), refusal="private refusal text"),
    completion(proposal(), finish="length"),
    {"choices": [{"finish_reason": "stop", "message": {"content": "not json"}}]},
    {"choices": [{"finish_reason": "stop", "message": {"content": '{"ambiguous":true,"ambiguous":false,"proposals":[]}'}}]},
])
def test_openai_malformed_refusal_and_incomplete_outputs_are_rejected(response):
    provider = OpenAIChatProvider("synthetic-api-key-not-real", transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)))
    with pytest.raises(AssistantInvalidOutput) as failure:
        provider.propose(FIELDS["applicant_full_name"], "Synthetic Nguyen")
    assert str(failure.value) == ""


@pytest.mark.parametrize("status", [400, 429, 500])
def test_openai_http_failures_have_no_retry_and_no_raw_error(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, text="synthetic-private-api-error")

    provider = OpenAIChatProvider("synthetic-api-key-not-real", transport=httpx.MockTransport(handler))
    with pytest.raises(AssistantUnavailable) as failure:
        provider.propose(FIELDS["applicant_full_name"], "Synthetic Nguyen")
    assert str(failure.value) == ""
    assert len(calls) == 1


def test_openai_timeout_is_bounded_and_not_retried():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("synthetic-private-timeout-details", request=request)

    provider = OpenAIChatProvider("synthetic-api-key-not-real", transport=httpx.MockTransport(handler))
    with pytest.raises(AssistantTimeout) as failure:
        provider.propose(FIELDS["applicant_full_name"], "Synthetic Nguyen")
    assert str(failure.value) == ""
    assert len(calls) == 1
