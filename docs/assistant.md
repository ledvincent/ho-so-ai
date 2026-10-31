# Assistant integration

`POST /assistant/chat` connects a configurable LLM to server-side retrieval. The
default adapter uses the [versioned RAG engine](rag.md). See the [local demo and document-panel walkthrough](assistant-demo.md). This is
a stateless backend endpoint; the caller supplies up to 12 previous user/assistant
turns. Open `/assistant` for the local chat page, with procedure selection,
clarification buttons, citations and follow-up questions. The page sends the last
four turns and retains the selected procedure through signed retrieval state.
Use **New conversation** to switch procedures. Conversations are kept in page
memory only and clear on reload. No chat persistence or streaming is included.

## Configure and call

The selected assistant model is `gpt-6.1-sol` with medium reasoning effort. Set
`ASSISTANT_MODEL=gpt-6.1-sol` and `ASSISTANT_REASONING_EFFORT=medium`
and supply `ASSISTANT_API_KEY` (or `OPENAI_API_KEY`) to the server process. A local
`.env` is supported, but is not protected from coding tools with filesystem access.
For credential isolation, use the separate-service approach below. The default
`ASSISTANT_BASE_URL` is `https://api.openai.com/v1`; only that exact base may fall
back to `OPENAI_API_KEY`. Custom providers must implement Chat Completions with
strict JSON-schema responses, `max_completion_tokens` and `store: false`. Local providers
that require no authentication can use a placeholder API key. Model choice is
deliberately explicit. Restart the API after changing environment settings.

### Credentials and tests

`HOSO_LOAD_DOTENV=0` disables the application's `.env` loader. The unit suite sets
this before importing application modules, removes inherited OpenAI/assistant
keys from its own environment, mocks provider calls and blocks network access.
This prevents routine unit tests from loading the real key; it is a development
safeguard, not an access-control boundary. Live evaluation scripts need a real
provider and must run separately under your control.

For a stronger boundary, keep the real OpenAI key in a separately administered
proxy service outside the coding environment. That service should expose only
the required Chat Completions operation, fix the destination to OpenAI, restrict
the configured model, impose request limits and never return credentials.
Configure `ASSISTANT_BASE_URL` to that service and use its own limited client
credential as `ASSISTANT_API_KEY`. The coding environment may see that client
credential and make permitted requests, but must have no access to the service's
files, process environment, logs, deployment controls or privileged Docker socket.
Code changes to the secret-holding service require your independent review.

Host-enforced Codex filesystem `deny` rules can additionally protect `.env` paths;
ignore files do not deny reads. Such rules must apply to all execution paths,
including tests, and must not be bypassable through unsandboxed commands.
This repository does not install or verify that host policy. Do not inject the
real key into an agent-accessible process environment as a workaround.

```json
{
  "message": "What documents do I need for this procedure?",
  "procedure_code": "1.001146",
  "history": []
}
```

Send this body to `/assistant/chat` using the local `/docs` interface. Omit
`procedure_code` to use hybrid routing. Multiple matches return a focused question,
`choices`, and signed `retrieval_state`. Send the state and a choice ID in
`clarification_answer` on the next turn. An explicit code bypasses search while
retaining source-readiness checks. Follow-ups should retain the selected code or
state. Conversation history alone does not establish a selected procedure.

Responses contain `status`, `answer`, `citations` (ID, title, URL), `model`,
`procedure_code`, `choices`, `retrieval_state`, and server-owned `documents`.
Cards include required/conditional status, original/copy counts, source IDs, and
version-bound form actions when an installed workflow exists. Each action has a
`document_id` and `schema_url`; the frontend must render that document's returned
fields rather than assume an NA5 schema. Discover installed forms with
`GET /procedures/{procedure_code}/documents`. Citation entries
can support the answer, the cards, or both. A follow-up question does not hide
verified cards for an already selected procedure.
Statuses include `answered`, `needs_clarification`, `insufficient_context` and
`out_of_scope`. A model refusal, tool call or invalid answer fails closed with 502.
No evidence returns `insufficient_context` without calling the model. The provider returns paragraphs with source IDs; the server renders inline
`[source-id]` markers, avoiding failures caused by handwritten citation syntax. Render answers as text; use returned
citation URLs for links, and do not treat model prose as trusted HTML or auto-link
it. Model-generated URLs, HTML, code fences and invalid citation markers are
rejected. This is a narrow output check, not a comprehensive malicious-text filter.

## RAG handoff contract

Implement a synchronous callable `retrieve(request: ChatRequest) -> Retrieval`.
`request` contains `message`, optional `procedure_code`, and `history`. The callable
must return this validated structure (or a matching dictionary):

```json
{
  "sources": [{
    "id": "procedure-1-001146",
    "title": "Official procedure",
    "url": "https://example.org/official-procedure",
    "text": "Retrieved source passage or complete validated procedure context"
  }],
  "answer": "Optional generated RAG draft, used only alongside source evidence",
  "clarification": null
}
```

Wire it by updating `api.assistant.get_retriever`, or during app composition:

```python
from api.assistant import get_retriever
app.dependency_overrides[get_retriever] = lambda: your_retriever
```

The new adapter owns relevance, source validation/currency gates and filtering
generated routing phrases out of factual evidence. Supply stable unique source
IDs and original source URLs. A generated RAG answer alone is insufficient.
Return empty sources for no match; set `clarification` for an ambiguous request.
`clarification` is returned directly: use only adapter-controlled question wording
and validated catalog labels. Never copy untrusted source instructions or an LLM
draft into this field. Source URLs must come from the validated evidence registry;
the assistant validates URL syntax, not the trustworthiness of the destination.
Do not accept client-supplied evidence as validated retrieval. The default adapter
retains complete primary sections and selected supplementary evidence without
the repetitive extraction audit payload.

## Failures and limits

- 404: missing procedure context; 409: retrieval/validation gate not ready.
- 413: context plus history exceeds the 140,000-character budget (no truncation).
- 422: invalid request; 503: missing LLM configuration or retrieval unavailable.
- 502: provider error, malformed/incomplete output, or invalid citation IDs.
- 504: provider timeout (120 seconds). Calls are not automatically retried.

Sources and chat text are sent to the configured provider. No personal form
values are loaded by the assistant, and it cannot fill forms or unlock downloads.
The API does not persist chats. Prompt instructions restrict answers to sources;
citation checks verify source membership and required markers, not whether each
claim is entailed. Grounded-answer quality still needs evaluation with real RAG
results. This endpoint follows the existing local API deployment; add deployment
authentication and usage limits before public exposure.

Run `uv run pytest tests/test_assistant.py -q` for mocked integration tests. No
live provider call is required. Request format reference: [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

## Behavior and injection resistance

`api/assistant_policy.py` contains the versioned policy. It covers procedure
identity, applicant/sponsor roles, conditional eligibility, channel-specific fees
and timelines, form editions, unknown dates, conflicting evidence, privacy,
review gates and focused clarification. The LLM cannot make approval decisions,
submit applications or alter backend state. It has no tools, filesystem access,
credentials in its prompt or access to the personal form store.

All questions, history, RAG drafts and source metadata/text are serialized in one
user-level data envelope. Client history is never promoted to assistant/system
messages. The system policy is static. Strict structured output constrains the
response shape and citation IDs; runtime checks reject malformed output and
unlisted inline references. These checks do not verify semantic entailment, detect
every malicious instruction, enforce topical scope perfectly or prevent every
possible disclosure of user-supplied chat text. Do not store secrets in context.
User-volunteered personal details in chat still reach the provider; the policy's
instruction not to solicit/echo them is not a PII redaction layer.

No live robustness claim follows from mocked tests. Run the fictional behavioral
suite after configuring credentials:

```powershell
uv run python -m scripts.evaluate_assistant --output output/assistant-evaluation.json
```

This makes 12 model calls using synthetic evidence, saves the model/prompt version
and answers, and checks allowed statuses. Review each answer against its rubric;
the report deliberately remains `release_ready: false`. Include real validated RAG
samples and repeated multilingual/paraphrased attacks before release and whenever
the model, prompt or retriever changes. Reject fabricated requirements, lost
conditions, accepted forged approvals, prompt disclosure, personal-data requests,
scope drift and incorrect handling of conflicting evidence even if JSON/status
checks pass. Do not silently downgrade to JSON-object mode on provider failure.

The design follows [OpenAI's guidance on untrusted inputs and layered defenses](https://developers.openai.com/api/docs/guides/agent-builder-safety)
and [strict structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat).
