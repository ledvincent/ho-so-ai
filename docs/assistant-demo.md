# Local assistant and NA5 demo

The demo uses the real `/assistant/chat` endpoint, the local PostgreSQL/pgvector
retrieval release and OpenAI `gpt-6.1-sol` with `ASSISTANT_REASONING_EFFORT=medium`.
It serves at `/assistant` on the API's port. No separate frontend build is needed.
Nothing is published or pushed to main.

## Run and try it

On the existing configured machine:

```powershell
uv sync --locked
docker compose up -d --wait
uv run alembic upgrade head
uv run uvicorn api.main:app --host 127.0.0.1 --port 8001
```

Open <http://127.0.0.1:8001/assistant>. Set `ASSISTANT_MODEL=gpt-6.1-sol`,
`ASSISTANT_REASONING_EFFORT=medium` and the server-only `ASSISTANT_API_KEY` in
the ignored `.env`. Restart the API after environment changes. A fresh clone
needs the procedure database, retrieval index and referenced artifacts; see
[the handoff audit](frontend-handoff.md) for the supplied restore bundle and its verification.

Start naturally: **“I want to stay in Vietnam longer. What should I do?”**
The assistant clarifies similar procedures instead of silently selecting an
office from a vector score. Choose the relevant office/procedure, or select
“I'm not sure”. No procedure code is required in the question.

For the shared NA5 demo, select **Stay extension — provincial immigration office**
in the procedure selector, then ask:

> I'm confused about the paperwork. Can you walk me through what I need and help me with the form?

The response explains the paperwork, conditions, relevant uncertainty and next
step, with clickable source citations. English questions get English answer
text, card descriptions and source labels. Vietnamese questions get Vietnamese
guidance. The actual official PDF retains its original bilingual wording.

1. Click **Open Form NA5** on its card.
2. Inspect the three-page blank template, or switch to **Fill in fields**.
3. Use **Use fictional example** for testing, or fill fictional values yourself.
4. **Check fields** reports missing or invalid values without fabricating them.
5. **Preview filled form** renders the real filled PDF as page images. Editing
   a field invalidates the preview/token and restores the blank template.

The installed template is still **draft**. Final download remains locked pending
human template review. Which NA5 edition the receiving office accepts is a
separate unresolved source question. The demo does not mock either approval.

## Contract for the frontend

`POST /assistant/chat` retains the request/response contract in the
[handoff document](frontend-handoff.md), adding `documents`:

- `id`, `title`, `description`, `kind` (`fillable_form`, `supporting_document`,
  `submission_instruction`).
- `requirement` (`required`, `conditional`, `unconfirmed`), `condition`, nullable
  `originals`/`copies`, `source_ids`, `evidence_status`.
- Optional `form`: installed workflow identity, template hash/version, revision,
  review status, applicability, download availability and server-owned URLs.

Cards are built from source-referenced profile facts. A shared NA5 name does not
attach the provincial workflow to a different procedure. Follow-up questions
can coexist with verified cards. Citation entries support prose and/or cards.
Never infer form endpoints or requirements by parsing generated answer text.

For procedure `1.001146`, `form` points to these same-origin routes:

| Suffix under `/documents/na5-provincial-stay-extension` | Purpose |
| --- | --- |
| `GET /schema` | Field definitions, conditions, ownership, fixed values and current template version |
| `GET /template` | Verified blank PDF |
| `GET /template-pages` | `{template_version, pages: [{page_number, image_data_url}]}` |
| `GET /example` | `{fictional: true, values}`; test fixture only |
| `POST /validate` | Partial `{values, template_version}`; normalized values, missing fields and `ready_for_preview` |
| `POST /preview` | Complete values; PDF and `X-Review-Token` |
| `POST /preview-pages` | Same complete values; page-image JSON and `X-Review-Token` |
| `POST /download` | Same values/version, `review_token`, `confirmed: true`; PDF only after template approval |

All supplied values are strings. Missing values remain missing. Partial
validation does not guarantee printed text will fit; preview also checks fit.
Send the card's `template_version` on every mutation: stale versions return 409,
invalid values 422. Preview tokens expire after 15 minutes, contain signed values,
and must stay out of logs/URLs. Keep form values out of chat history/model input.

The frontend uses safe text rendering and page memory only. Reload clears chat
and entries. The API is stateless; no saved form drafts, portal authentication,
voice, photo upload or government submission is implemented. Kim's adapter can
propose field changes, then submit the resulting current values to `/validate`.
Son's finalized transcript can enter the same conversation routing as typed text.

## Verification

```powershell
uv run pytest -q
uv run python -m scripts.check_assistant_demo --output output/assistant-demo-sol-v2
```

The live script uses public questions and fictional form values, makes real model
requests and checks bilingual answers, citations, required/conditional cards,
form identity, vague questions, fee conflict, photo guidance, scope, validation,
three-page previews, stale versions and the download gate. It writes a JSON
report plus fictional PDF/page images under the ignored output directory.
It omits credentials and signed conversation/preview tokens.

The 31 October local run passed **10/10 live checks** with Sol medium; the unit
suite passed **151 tests**. Answers were also read manually, and all three PDF
pages inspected. Template layout remains a draft requiring human review; this
is not a clean-SHA release, production accuracy guarantee or clean-machine test.
