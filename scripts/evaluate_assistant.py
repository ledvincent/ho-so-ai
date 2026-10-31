"""Explicit live evaluation using fictional evidence; never loads applicant data.

Run: python -m scripts.evaluate_assistant --output output/assistant-evaluation.json
Status checks are automatic; every semantic rubric still requires human review.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from api.assistant import ChatRequest, Retrieval, Source, generate
from api.assistant_policy import POLICY_VERSION, PROMPT
from api.config import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads((ROOT / "tests/fixtures/assistant_behavior.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        request = ChatRequest(message=case["question"], history=case.get("history", []))
        evidence = Retrieval(sources=[Source(id="s1", title="Fictional evaluation evidence",
            url="https://example.org/fixture", text=case["source"])], answer=case.get("draft"))
        row = {"id": case["id"], "rubric": case["rubric"], "semantic_review": "pending"}
        try:
            result, model = generate(request, evidence)
            row.update(model=model, result=result.model_dump(),
                       status_check=result.status in case["expected_status"])
        except HTTPException as exc:
            row.update(error=exc.detail, http_status=exc.status_code, status_check=False)
        results.append(row)
        if row.get("http_status") == 503:
            break  # Missing configuration: do not issue the remaining calls.
    report = {"policy_version": POLICY_VERSION,
              "prompt_sha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
              "created_at": datetime.now(timezone.utc).isoformat(),
              "cases_planned": len(cases), "results": results,
              "release_ready": False, "note": "Human semantic review required; status checks are not injection-resistance proof."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Recorded {len(results)} cases; semantic review pending: {args.output}")
    if len(results) != len(cases) or any(not r["status_check"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
