"""Explicit two-request fictional live check; no retries and no key access here."""

import argparse
from uuid import uuid4

import httpx

from check_local_http import checked_origin, login, response_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--web-origin", default="http://127.0.0.1:3016")
    parser.add_argument("--allow-live", action="store_true")
    args = parser.parse_args()
    if not args.allow_live:
        parser.error("This check makes up to two real model requests; explicit --allow-live is required.")
    origin = checked_origin(args.web_origin)
    calls = 0
    with httpx.Client(base_url=origin, timeout=30, trust_env=False, follow_redirects=False) as client:
        try:
            login(client, origin, "admin", "admin")
            before = response_data(client.get("/api/profile"), 200)
            assert before["revision"] == 2 and before["fields"]["full_name"] == "SYNTHETIC AUTH-02 A EDITED"
            print("PASS profile_persisted_across_api_process_restart", flush=True)

            def proposal(name, revision, values):
                nonlocal calls
                request_id = "live-fictional-" + uuid4().hex
                calls += 1
                response = client.post("/api/chat/assist", headers={"Origin": origin}, json={
                    "request_id": request_id, "draft_revision": revision,
                    "procedure_code": "1.001146", "intent": "form_answer",
                    "focus_field": "applicant_full_name",
                    "message": "Please use this exact fictional full name: " + name,
                    "values": {"request_type": "stay_extension", **values},
                })
                if response.status_code != 200:
                    print(f"FAIL live_request_{calls} http_status={response.status_code}", flush=True)
                    raise RuntimeError("Live request failed; no automatic retry.")
                data = response_data(response, 200)
                assert data["request_id"] == request_id and data["draft_revision"] == revision
                assert data["status"] == "proposed" and data["review_status"] == "draft"
                assert data["proposed_changes"] == [{"field_id": "applicant_full_name", "value": name}]
                assert data["next_field"] == "sex" and data["assistant_text"]
                print(f"PASS live_request_{calls} validated_na5_proposal", flush=True)

            proposal("Synthetic Nguyen Alpha", 3, {})
            proposal("Synthetic Nguyen Beta", 4, {"applicant_full_name": "Synthetic Nguyen Alpha"})
            assert response_data(client.get("/api/profile"), 200) == before
            print("PASS live_proposals_do_not_save_profile", flush=True)
            print(f"PASS live_request_count={calls} no_retries", flush=True)
            return 0
        except Exception:
            print(f"STOP live_check requests_started={calls}; no retries", flush=True)
            return 1
        finally:
            try:
                client.post("/api/auth/logout", json={}, headers={"Origin": origin})
            except Exception:
                print("WARN test_session_logout_unconfirmed", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
