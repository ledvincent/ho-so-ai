"""Actual LOCAL HTTP acceptance against already-running loopback servers.

Requires the dedicated checkpoint database, its explicit synthetic-account seed,
and absent admin/reviewer profiles before the first run. Writes fictional profiles
through HTTP only, then revokes test sessions. Never resets a database, starts or
stops a server, reads keys/env files, or sends a model-backed form message.
Output is limited to static check names and counts; no responses or credentials.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie
import re
import time
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

import httpx


COOKIE = "hoso_local_session"
WORKFLOW_SHA256 = "50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3"


def checked_origin(value: str) -> str:
    parsed = urlsplit(value)
    assert parsed.scheme in {"http", "https"}
    assert parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    assert parsed.username is None and parsed.password is None
    assert not parsed.path and not parsed.query and not parsed.fragment
    assert parsed.port is not None
    return value


def response_data(response: httpx.Response, status: int) -> dict:
    assert response.status_code == status
    assert "no-store" in response.headers.get("cache-control", "").lower()
    value = response.json()
    assert isinstance(value, dict)
    return value


def error_code(response: httpx.Response) -> str | None:
    data = response.json()
    detail = data.get("detail")
    return detail.get("code") if isinstance(detail, dict) else data.get("code")


def fictional_fields(account: str, *, edited: bool = False) -> dict:
    return {
        "full_name": f"SYNTHETIC AUTH-02 {account}" + (" EDITED" if edited else ""),
        "date_of_birth": "1990-01-02",
        "nationality": "Synthetic test value",
        "address": f"Synthetic test address {account}",
        "phone_number": None,
        "email": f"synthetic-{account.lower()}@example.invalid",
    }


def login(client: httpx.Client, origin: str, username: str, password: str) -> tuple[dict, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password}, headers={"Origin": origin})
    data = response_data(response, 200)
    assert set(data) == {"user", "expires_at"}
    assert set(data["user"]) == {"id", "username", "identity_provider"}
    assert data["user"]["username"] == username and data["user"]["identity_provider"] == "local"
    assert isinstance(data["user"]["id"], str) and data["user"]["id"]
    assert type(data["expires_at"]) is int and data["expires_at"] > time.time()
    selected = None
    for header in response.headers.get_list("set-cookie"):
        cookies = SimpleCookie()
        cookies.load(header)
        if COOKIE in cookies:
            selected = cookies[COOKIE]
    assert selected is not None
    assert selected["httponly"] and selected["samesite"].lower() == "lax"
    assert selected["path"] == "/" and not selected["domain"]
    assert bool(selected["secure"]) == (urlsplit(origin).scheme == "https")
    assert re.fullmatch(r"[A-Za-z0-9_-]{40,256}", selected.value)
    assert abs(parsedate_to_datetime(selected["expires"]).timestamp() - data["expires_at"]) <= 1
    assert selected.value not in response.text
    return data, f"{COOKIE}={selected.value}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic LOCAL HTTP acceptance; no model calls.")
    parser.add_argument("--web-origin", default="http://127.0.0.1:3016")
    parser.add_argument("--api-origin", default="http://127.0.0.1:8016")
    parser.add_argument("--check-unavailable-retrieval", action="store_true",
                        help="Also check the current hardcoded procedure-question 503; no retrieval/model adapter is invoked.")
    args = parser.parse_args()
    current = "configuration"
    passed = 0

    def check(name: str, action):
        nonlocal current, passed
        current = name
        value = action()
        passed += 1
        print(f"PASS {name}", flush=True)
        return value

    active: list[httpx.Client] = []
    web = ""
    try:
        web = checked_origin(args.web_origin)
        api = checked_origin(args.api_origin)
        with ExitStack() as stack:
            def client(base: str) -> httpx.Client:
                return stack.enter_context(httpx.Client(base_url=base, timeout=30, follow_redirects=False, trust_env=False))

            anonymous, a, b, backend = client(web), client(web), client(web), client(api)
            mutation = {"Origin": web}

            def cleanup_sessions():
                # ExitStack runs this before it closes any of the HTTP clients.
                for owner in tuple(active):
                    try:
                        owner.post("/api/auth/logout", json={}, headers=mutation)
                    except Exception:
                        pass
            stack.callback(cleanup_sessions)

            def anonymous_apis():
                for path in ["/api/auth/session", "/api/profile", "/api/chat/schema"]:
                    response_data(anonymous.get(path), 401)
                for path in ["/api/chat/assist", "/api/forms/demo/preview", "/api/forms/demo/pdf"]:
                    response_data(anonymous.post(path, json={}, headers=mutation), 401)
                for path in ["/v1/profile", "/v1/chat/schema", "/v1/forms/demo"]:
                    response_data(backend.get(path), 401)
                for path in ["/v1/chat/assist", "/v1/forms/demo/preview", "/v1/forms/demo/pdf"]:
                    response_data(backend.post(path, json={}, headers=mutation), 401)
            check("unauthenticated_apis", anonymous_apis)

            def private_pages():
                for path in ["/portal", "/workspace", "/chat", "/forms/demo", "/research",
                             "/documents/example.pdf", "/demo/workspace", "/workspace/secret.txt"]:
                    response = anonymous.get(path)
                    assert response.status_code in {302, 303, 307, 308}
                    location = urlsplit(urljoin(web + "/", response.headers["location"]))
                    assert f"{location.scheme}://{location.netloc}" == web and location.path == "/login"
                    assert "no-store" in response.headers.get("cache-control", "").lower()
            check("protected_pages_and_dotted_path", private_pages)

            def hostile_origin():
                response = anonymous.post("/api/auth/login", json={"username": "admin", "password": "admin"},
                                          headers={"Origin": "http://hostile.example.invalid"})
                response_data(response, 403)
                assert error_code(response) == "ORIGIN_FORBIDDEN"
                assert not response.headers.get_list("set-cookie")
            check("hostile_origin_login_denied", hostile_origin)

            def invalid_login():
                errors = []
                for username, password in [("admin", "synthetic-wrong-password"), ("synthetic_absent_user", "synthetic-wrong-password")]:
                    response = anonymous.post("/api/auth/login", json={"username": username, "password": password}, headers=mutation)
                    errors.append(response_data(response, 401))
                    assert error_code(response) == "INVALID_CREDENTIALS"
                    assert not response.headers.get_list("set-cookie")
                assert errors[0] == errors[1] == {"detail": {"code": "INVALID_CREDENTIALS"}}
            check("invalid_login_generic", invalid_login)

            active.append(a)
            identity_a, cookie_a = check("login_a_cookie_and_dto", lambda: login(a, web, "admin", "admin"))
            active.append(b)
            identity_b, cookie_b = check("login_b_cookie_and_dto", lambda: login(b, web, "reviewer", "reviewer-demo"))

            def sessions():
                assert response_data(a.get("/api/auth/session"), 200) == identity_a
                assert response_data(b.get("/api/auth/session"), 200) == identity_b
                assert identity_a["user"]["id"] != identity_b["user"]["id"]
            check("session_info_isolated", sessions)

            def fresh_profiles():
                response_data(a.get("/api/profile"), 404)
                response_data(b.get("/api/profile"), 404)
            check("dedicated_profiles_initially_empty", fresh_profiles)

            def put(owner: httpx.Client, revision: int, fields: dict, status: int = 200) -> dict:
                data = response_data(owner.put("/api/profile", json={"expected_revision": revision, "fields": fields}, headers=mutation), status)
                if status == 200:
                    assert set(data) == {"profile_id", "revision", "fields"}
                    assert type(data["revision"]) is int and data["revision"] == revision + 1
                    assert isinstance(data["profile_id"], str) and data["profile_id"]
                    assert data["fields"] == fields
                return data

            profile_a = check("profile_a_create_revision_zero", lambda: put(a, 0, fictional_fields("A")))

            def b_cannot_select_a():
                response_data(b.get("/api/profile"), 404)
                put(b, profile_a["revision"], fictional_fields("B"), 404)
            check("profile_b_cannot_access_a", b_cannot_select_a)

            def create_b():
                data = put(b, 0, fictional_fields("B"))
                assert profile_a["profile_id"] != data["profile_id"]
                return data
            profile_b = check("profile_b_create_revision_zero", create_b)

            def edit_a():
                data = put(a, 1, fictional_fields("A", edited=True))
                assert data["profile_id"] == profile_a["profile_id"]
                return data
            edited_a = check("profile_a_explicit_edit", edit_a)

            def independent_edits():
                assert response_data(b.get("/api/profile"), 200) == profile_b
                edited_b = put(b, 1, fictional_fields("B", edited=True))
                assert edited_b["revision"] == 2 and edited_b["profile_id"] == profile_b["profile_id"]
                assert response_data(a.get("/api/profile"), 200) == edited_a
                assert response_data(b.get("/api/profile"), 200) == edited_b
            check("profile_edits_independent", independent_edits)

            def stale_revision():
                put(a, 1, fictional_fields("SHOULD_NOT_PERSIST"), 409)
                put(a, 0, fictional_fields("SHOULD_NOT_PERSIST"), 409)
                assert response_data(a.get("/api/profile"), 200) == edited_a
            check("stale_revision_and_duplicate_create_denied", stale_revision)

            def owner_injection():
                response = a.put("/api/profile", json={"expected_revision": 2, "fields": fictional_fields("A"),
                                                      "owner_subject": identity_b["user"]["id"]}, headers=mutation)
                response_data(response, 422)
                assert response_data(a.get("/api/profile"), 200) == edited_a
            check("client_owner_injection_denied", owner_injection)

            def schema():
                data = response_data(a.get("/api/chat/schema"), 200)
                assert data["procedure_code"] == "1.001146" and data["review_status"] == "draft"
                assert data["schema_version"] == WORKFLOW_SHA256
                assert len(data["fields"]) == 43 and len({field["id"] for field in data["fields"]}) == 43
                assert data["fixed_values"]["request_type"] == "stay_extension"
                return data
            schema_data = check("draft_schema_exact_43_fields", schema)

            def initial_question():
                request_id = "http-smoke-initial-" + uuid4().hex
                response = a.post("/api/chat/assist", json={"request_id": request_id, "draft_revision": 3,
                    "procedure_code": "1.001146", "intent": "form_answer", "message": "", "focus_field": None,
                    "values": {"request_type": "stay_extension"}}, headers=mutation)
                data = response_data(response, 200)
                assert data["request_id"] == request_id and data["draft_revision"] == 3
                assert data["status"] == "question" and data["proposed_changes"] == []
                assert data["next_field"] in {field["id"] for field in schema_data["fields"]}
                assert data["schema_version"] == WORKFLOW_SHA256 and data["review_status"] == "draft"
                assert isinstance(data["assistant_text"], str) and data["assistant_text"]
                assert response_data(a.get("/api/profile"), 200) == edited_a
            check("empty_message_question_no_profile_write", initial_question)

            if args.check_unavailable_retrieval:
                def unavailable_retrieval():
                    response = a.post("/api/chat/assist", json={"request_id": "http-smoke-procedure-" + uuid4().hex,
                        "draft_revision": 3, "procedure_code": "1.001146", "intent": "procedure_question",
                        "message": "Synthetic procedure question", "focus_field": None, "values": {}}, headers=mutation)
                    response_data(response, 503)
                    assert error_code(response) == "RETRIEVAL_UNAVAILABLE"
                check("procedure_retrieval_explicitly_unavailable", unavailable_retrieval)

            def logout_and_revoke(owner: httpx.Client, old_cookie: str):
                response = owner.post("/api/auth/logout", json={}, headers=mutation)
                assert response_data(response, 200) == {"ok": True}
                assert any("Max-Age=0" in header for header in response.headers.get_list("set-cookie"))
                response_data(anonymous.get("/api/auth/session", headers={"Cookie": old_cookie}), 401)
                response_data(anonymous.get("/api/profile", headers={"Cookie": old_cookie}), 401)
                token = old_cookie.partition("=")[2]
                response_data(backend.get("/v1/auth/session", headers={"Authorization": "Bearer " + token}), 401)
                active.remove(owner)
            check("logout_a_revokes_old_cookie", lambda: logout_and_revoke(a, cookie_a))
            check("logout_b_revokes_old_cookie", lambda: logout_and_revoke(b, cookie_b))
        print(f"PASS {passed} checks", flush=True)
        return 0
    except Exception:
        print(f"FAIL {current}", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
