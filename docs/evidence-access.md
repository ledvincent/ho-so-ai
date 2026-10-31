# Scoped evidence access

Migration 0009 adds `procedure_analysis.evidence_status`. The legacy `facts_ready` value is retained as historical ingestion output. A separate scoped review permits source-attributed answers for the exact ingestion run and profile; new runs and unknown blocks remain blocked. Template approval and original-file associations are unchanged.

The four reviews are recorded in `data/reviews/`. Procedure currency remains `not_reverified`, form applicability `unresolved`, and conflicting facts retain both source references. Official checks confirmed the gazette effective date of 70/2026/TT-BCA and the Can Tho provincial page naming that NA5 revision; they do not establish the current validity of all four procedures.

For these small reviewed records, RAG supplies all captured primary, supplementary and form evidence grouped by original URL. This preserves opposing evidence instead of losing it through top-k ranking. Budget limits still apply. The assistant may answer unaffected questions; relevant fee/version conflicts require a qualified partial answer. This is a model behavior policy, not a guarantee of semantic correctness.

Run `python -m scripts.check_scoped_answers` for a live non-personal conversation trace, saved under ignored `output/`. The standard RAG smoke test still checks unknown-block and stale-membership rejection. Reviews do not require re-embedding because source bodies and retrieval membership are unchanged.
