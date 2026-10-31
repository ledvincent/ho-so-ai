# Assistant integration

`POST /assistant/chat` connects a configurable LLM to server-side retrieval. The
existing search, context validation and form-filling code are unchanged. This is
a stateless backend endpoint; the caller supplies up to 12 previous user/assistant
turns. No chat UI, chat persistence or streaming is included yet.

## Configure and call

The selected assistant model is `gpt-4o-mini`. Set `ASSISTANT_MODEL=gpt-4o-mini`
and `ASSISTANT_API_KEY` (or `OPENAI_API_KEY`) in `.env`. The default
`ASSISTANT_BASE_URL` is `https://api.openai.com/v1`; only that exact base may fall
back to `OPENAI_API_KEY`. Custom providers must implement Chat Completions with
strict JSON-schema responses, `max_completion_tokens` and `store: false`. Local providers
that require no authentication can use a placeholder API key. Model choice is
deliberately explicit. Restart the API after changing environment settings.

```json
{
  "message": "What documents do I need for this procedure?",
  "procedure_code": "1.001146",
  "history": []
}
```

Send this body to `/assistant/chat` using the local `/docs` interface. Omit
`procedure_code` to route through existing search (requires a calibrated index).
Multiple matches return `needs_clarification`; resubmit with the chosen code.
An explicit code bypasses search but still calls the validated context loader.
Every follow-up should retain the selected code. Retrieval uses the current
message, not conversation history; custom RAG can use history to resolve follow-ups.

Responses contain `status`, `answer`, `citations` (ID, title, URL) and `model`.
Statuses include `answered`, `needs_clarification`, `insufficient_context` and
`out_of_scope`. A model refusal, tool call or invalid answer fails closed with 502.
No evidence returns `insufficient_context` without calling the model. Generated
answers have inline `[source-id]` markers. Render answers as text; use returned
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
preserves the entire existing procedure context rather than summarizing it.

## Failures and limits

- 404: missing procedure context; 409: retrieval/validation gate not ready.
- 413: context plus history exceeds the 140,000-character budget (no truncation).
- 422: invalid request; 503: missing LLM configuration or retrieval unavailable.
- 502: provider error, malformed/incomplete output, or invalid citation IDs.
- 504: provider timeout (60 seconds). Calls are not automatically retried.

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
