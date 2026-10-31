# Frontend compatibility check — 31 October 2026

Compared backend `7c78ec4` with Kim's fetched branch
`codex/kim/ui-03-chat-first-discovery` at
`1825f5e15cf84fc6259004c56cec7185799ae12c`. This is a source-code review,
not a claim that the two services passed an end-to-end portal test.

Kim has the API schemas and examples needed to implement the remaining wiring.
His current adapter still rejects the new contract. Make these changes before
calling the integration complete:

| Area | Current adapter | Required update |
| --- | --- | --- |
| Chat response | `web/lib/discovery/upstream.ts` allows only status/answer/citations/model | Accept and render `documents`, `choices`, `procedure_code`, and opaque `retrieval_state` |
| Clarification input | Both `handler.ts` and `upstream.ts` reject additional request fields | Accept/forward `retrieval_state` and `clarification_answer`; omit explicit procedure code during a pending choice |
| Document schema | Hard-coded procedure/hash, exactly 43 fields, local NA5 JSON equality | Fetch returned `form.schema_url` by `document_id`; use returned fields, conditions, fixed values and template version |
| Readiness | Blocks schema whenever `facts_ready` is false | Treat source currency, document applicability, template review and download availability separately; scoped source answers and draft preview are intentionally available |
| Document actions | Proxy allowlist has no generic document routes | Add explicit allowed schema/template/validate/preview/download routes; preserve binary content, no-store and `X-Review-Token`. Resolve server-owned action URLs against the configured upstream, never arbitrary user URLs |
| Search | Requires a numeric `similarity` on every result | New hybrid results expose `score` and `matched_by`; do not require the old similarity field. Handle unavailable/degraded search |
| Timeouts/history | Chat 65 seconds; history content 8,000 characters | Allow at least 180 seconds upstream (model limit 120 plus retrieval); align with the backend's 16,000-character per-turn contract |

Use [the committed OpenAPI and real examples](contracts/README.md) as fixtures
for the adapter tests. Then exercise login → broad question → clarification →
document card → schema → partial validation → actual preview. A draft download
must show the expected 409 limitation rather than be bypassed.

## Environment and routing

Kim's `web/lib/server/discovery-proxy.ts` is already a server-side proxy that
checks the portal session. Set this in **Kim's `web/.env.local`** (it was missing
from the inspected `web/.env.example`):

```dotenv
HOSO_VINCENT_API_URL=http://127.0.0.1:8001
```

This address works when the portal server and this backend run on the same host.
On separate hosts use the backend's reachable private address. Do not confuse
this setting with `HOSO_API_URL`, which routes to the separate authenticated
adapter API. Keep OpenAI credentials in this backend's `.env`, not browser config.
The current backend env example matches the local non-secret model settings:
assistant Sol medium, profile Sol medium, public-form mapping Astra high.
Real API keys and signing secrets are intentionally blank in `.env.example`.

Browser → same-origin portal `/api/discovery/*` → private backend requires **no
CORS middleware on this backend**. Keep that design. If the browser later calls
the backend directly on another origin, configure an exact origin allowlist,
GET/POST/OPTIONS and Content-Type as needed, and expose `X-Review-Token` and
`Content-Disposition`. CORS is browser access policy, not backend authentication.
See [FastAPI's CORS documentation](https://fastapi.tiangolo.com/tutorial/cors/).

## Remaining delivery limits

- Kim still needs the supplied database/public-file bundle and his own server key,
  or access to a configured private backend. A Git clone alone does not load data.
- No public HTTPS deployment has been delivered for this service.
- Only NA5 is installed so far; the schema/rendering contract supports other
  installed documents without a fixed frontend field list.
- Final NA5 download is gated by human template review; accepted edition remains
  unresolved in the captured evidence. These are actual limits, not UI mocks.
- Voice transport belongs to Son. Portal authentication, adapter validation and
  the final combined flow still need integration testing together.
