# RAG engine

PostgreSQL/pgvector holds the corpus, keyword index, vector index, embedding jobs,
and immutable release membership. The local Ollama service generates normalized
1024-dimensional BGE-M3 vectors. Public evidence only enters the corpus.

## Build and publish

```powershell
docker compose up -d db embeddings
docker compose exec embeddings ollama pull bge-m3
uv run alembic upgrade head
uv run python -m api.rag_index build
# Substitute the returned UUID in the following commands.
uv run python -m api.rag_index work --release RELEASE_UUID
uv run python -m api.rag_index status
uv run python -m api.rag_index publish --release RELEASE_UUID
uv run python -m scripts.evaluate_rag --release RELEASE_UUID
uv run python -m api.rag_index publish --release RELEASE_UUID --minimum CALIBRATED_THRESHOLD
```

Publishing without `--minimum` enables exact/keyword/typo routing only. Vectors
are still available for evidence ranking within a selected procedure. Do not
invent a threshold: the evaluation report proposes one using the calibration
split and reports a separate development test split. This small fixture is not
a production quality guarantee. Inspect candidate errors and expand the corpus.

`build` is idempotent for the same source/profile/model versions. It captures
all active validated profiles, including `needs_source_details` snapshots and
those currently blocked for answering. Missing fee/source details must not hide
a procedure from routing; the separate evidence-readiness check still prevents
unreviewed incomplete sources from being used for factual answers.
Embedding cache keys include exact input text and model configuration/digest.
Jobs are leased with `FOR UPDATE SKIP LOCKED`, use bounded attempts, record
failures, and retry after 30 seconds. Rerun `work` after a transient failure;
expired leases are reclaimed after ten minutes. Five failed attempts require
operator inspection. No model calls run inside database transactions.

`publish` requires complete embeddings and switches one serving pointer in a
transaction. The previous release remains stored. Publishing an earlier complete
release restores its pointer; it still cannot serve stale/inactive source or
profile versions. Run build/work/publish after ingestion changes. The model tag
must still resolve to the recorded digest; a changed model requires a new build.

## Search and conversation

`POST /search` accepts `{"query":"extend my stay"}` and returns procedure
candidates, their matched branches, release ID, and degradation status. Exact
codes bypass embedding calls. Keyword and vector candidates are independent,
and reciprocal rank fusion contributes once per procedure per branch so that
extra aliases do not boost a procedure unfairly. No-match and embedding-service
unavailability are distinct. SQL filters directly access indexed item tables;
HNSW iterative scanning is enabled for filtered retrieval.

`POST /assistant/chat` uses the new adapter by default. Clarification responses
include `choices` and a signed `retrieval_state`. Send that state back along with
`clarification_answer` set to an offered choice ID (or its label). A small set of
unambiguous English/Vietnamese action and office phrases is also recognized;
unknown or negated free text repeats the question instead of guessing:

```json
{
  "message": "Extend my stay",
  "retrieval_state": "TOKEN_FROM_PREVIOUS_RESPONSE",
  "clarification_answer": "0"
}
```

The token preserves candidates, asked questions, and release membership for 30
minutes. It contains no secrets; it is signed, not encrypted. Configure
`RAG_STATE_SECRET` consistently across workers. Without configuration, state is
process-local and expires on restart. Start without a token to change intent or
correct a previous answer. The selected code and refreshed token accompany an
answer; retain them for follow-ups. History alone is not trusted selection state.

Clarification asks about supported action and authority distinctions, then offers
procedure choices when ambiguity remains. Unknown metadata/answers never exclude
a candidate. Profile eligibility remains a validated draft and is not executed
as an automatic eligibility decision. The source profiles currently use varying
value vocabularies; broader eligibility filtering requires semantic review and
canonicalization first. Matching a form code does not establish a unique procedure.

## Evidence and readiness

The serving adapter rechecks active procedure, exact snapshot/profile membership,
and evidence access before loading evidence. Access requires `facts_ready` or a
scoped review bound to the exact ingestion run and profile. Unknown blocks and
stale membership return HTTP 409 without calling the answer model. A published
index never approves a source. See [scoped evidence access](evidence-access.md).
Form-field review remains independent.

Source sections and form pages get stable source IDs and original URLs/locators.
Chunks preserve exact offsets and overlap. For today's small procedures the full
primary source is retained; supplementary/form candidates are ranked within that
procedure and expanded to complete parent sections. For scoped reviews, all
captured primary, supplementary and form evidence is included, grouped by its
original URL, so competing versions remain visible. The model may answer
unaffected questions while qualifying relevant conflicts. Generated routing phrases,
extraction metadata, and repetitive fact/citation JSON are excluded. Context is
bounded explicitly; exceeding the budget fails rather than silently truncating
requirements. No model-dependent semantic citation-entailment guarantee is made.

## Verification

```powershell
uv run pytest -q
uv run python -m scripts.check_rag
uv run python -m scripts.check_profile_baseline
uv run python -m scripts.check_analysis
```

`check_rag` exercises the actual SQL, idempotency, cache reuse, publication gates,
readiness/inactive checks and compact evidence in a transaction that always rolls
back. It uses synthetic vectors for mechanics, not retrieval-quality claims.
`evaluate_rag` uses real embeddings, records the model/release and per-query scores,
and does not modify readiness or automatically configure thresholds.
