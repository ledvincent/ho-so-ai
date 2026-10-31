# PROFILE-UI-01 — review checkpoint

UI owner: Kim. **In review, implementation paused** on October 31, 2026.
No push, deployment or merge. The manager retains ownership of status publication.
The logo deliverables and UI-02/UI-03 previews remain preserved.

## Exact commits

- Branch: `codex/kim/profile-ui-01-consented-prefill`.
- Checkout: `C:/Users/Kim/Documents/ChatGPT/Hackathon/work/kim-profile-ui`.
- UI-03 base: `1825f5e15cf84fc6259004c56cec7185799ae12c`.
- Initial UI checkpoint: `8eefcde`.
- Backend producer: `33d1d3d03d98a6542ba80b16a8add8ad9eece10d`, consumed
  once as `b4b178f`; producer evidence `e3cad28dc251dac181a13f682182da5607346d05`
  consumed as `646b53d`.
- Final consumer code: **`9afe5d75bfc5ed9d7ed91040180a0e4b02d0a8c1`**.
- Contract: [profile-01-contract.md](profile-01-contract.md), SHA-256
  `3821c90d1eb21e95c31affd442667340b499b321791d041ce4e8fc8e0fe33df1`.

Generated types, handlers, storage and the v2 proxy come from the backend commit.
No schema, hash, original form, dependency or manifest was redesigned.
The two LOCAL server pages change only their error display; their authentication
guards and redirects are preserved.

## Delivered behavior

- Optional profile: basics, contact, passport and residence. Explicit save,
  local cancellation and confirmation before reloading discards unsaved edits.
  Complete snapshot on PUT; legacy nationality/address remain visible and read-only.
- After confirmation of the exact procedure/form/schema tuple: choose to use the
  profile or continue manually. Opening the workspace does not load the profile.
  Applicant confirmation precedes reading; separate confirmation of the intended
  passport precedes selection of its proposals.
- Each proposal displays its source and value, with correction and deselection.
  Phone, email and their combination are exclusive alternatives for one field.
  All existing answers remain locked. There is no implicit replacement.
- Before Apply: reread the session and profile; bind to account/session,
  profile ID/revision, procedure/hash/schema/epoch and draft revision.
  A save in another tab also invalidates the plan. Applying is one undoable
  change; local questions target missing fields.
  Document edits/undo never save the profile.
- VI/EN for the current LOCAL journey: login, workspace, profile, consent,
  proposals, local guidance, Q&A, preparation tracking, review, errors and privacy.
  Only the non-sensitive `hoso-ui-locale` preference is stored on the device.
  Language changes preserve the draft, unsaved edits, consent and selections,
  without remounting their components or adding a locale field to requests.
  Entered values, sources/citations and service responses retain their original
  language. Local field labels do not modify the schema or images.
- Explicit Q&A about the selected procedure, with history separate from personal
  field answers. Sending without a mode choice asks for the intended action.
  Q&A changes no fields; its contract does not guarantee an answer tied to the
  exact displayed form edition.
- Compact tracking of `requirements` rows, with exact text, quantities and
  `form_ids` associations resolved within the same response. These are not
  automatically mandatory documents: instructions, alternatives and unknown
  applicability remain indicated. Manual tracking never establishes dossier
  completeness or official approval. Full versions/hashes are in source details;
  other documents remain read-only/manual preparation. Changing procedure requires
  confirmation before clearing the draft.
- No producer catalog is available: an honest “catalog not connected” state,
  distinct from “no results.” A scenario catalog exists only on the labeled route.

## Observed verification

- **150 offline frontend tests passed**; output:
  `output/profile-ui-01/frontend-tests.txt`.
- After the final bounded wording adjustments: **10 focused checks passed**
  (locale, history metadata and requirements); **final Next/TypeScript build passed**,
  output: `output/profile-ui-01/final-build.txt`.
- **428 API tests passed**, with one existing Starlette/httpx deprecation warning.
  The initial run lacked a temporary-directory parent: 109 setup errors,
  followed by creation of the parent and a successful full rerun. No API fix.
- Read-only review: preservation of newer input after asynchronous failure,
  v1-compatible legacy email text, consent, revisions and atomic application.
- Browser: save/read-back of three ISO dates (birth, issue, expiry), cancellation
  without saving, conflict preserving edits, and optional profile completion.
  CUA date `fill` alone did not always trigger React state; native up/down keys
  triggered the edit, and read-back confirmed all three saved values.
- Browser: existing typed name preserved, passport initially unselectable,
  exclusive contact choice, proposal correction and nationality deselection.
  Explicit profile save in a second tab -> old plan cleared; fresh read ->
  eight-field Apply. The typed name remains intact and unresolved sex is asked
  next. One undo restores the draft containing only that name.
- Q&A through an explicit fixture: identical draft review before/after;
  ambiguous submission blocked pending mode choice. After a field answer,
  earlier UI messages retain their translation and change metadata.
- Locale: unsaved profile edit preserved VI -> EN; EN retained across reload
  and sign-out. Passport consent, contact selection and corrected value preserved
  VI -> EN -> VI. Source wording/alternatives and manual tracking remain unchanged.
- **Sequential** browser isolation, after the manager review ended: admin logout,
  reviewer login -> empty profile without admin data; logout and reload of the old
  tab -> login without a draft. The initial concurrent review shared the IAB cookie;
  it does not establish isolation between two simultaneous sessions.
- Composer: field bottom at **675.83/720 px** on desktop; **807.33/844 px** at
  390x844; **431.33/450 px** at 390x450, VI and EN. No horizontal overflow observed
  at 390 px. Short-viewport simulation, not a physical phone-keyboard test.

Zero profile reads before opt-in and revision rechecks are covered by client tests
and call-site inspection; no exhaustive browser network tracer was added.
Selection/Q&A scenarios are synthetic; save and prefill do use this preview's
authenticated API and SQLite storage.

Ignored screenshots in `output/profile-ui-01/`: `profile-en.jpg`,
`consent-en-desktop.jpg`, `consent-en-mobile.jpg`, `stale-proposals.jpg`,
`applied-review-en.jpg`, `dossier-en.jpg`, `short-mobile-en.jpg`, `short-mobile-vi.jpg`.

## Preview left running

- UI: `http://127.0.0.1:3022/login`; API: `http://127.0.0.1:8022`.
- Offline scenarios: `http://127.0.0.1:3022/workspace/scenarios`.
- Local demonstration accounts: `admin / admin`, `reviewer / reviewer-demo`.
- Isolated database, new for this checkpoint: `api/tmp/profile-ui-preview.sqlite`, ignored.
  Fictional data only; no session, secret or database file is committed.
- UI-02 `3018/8018` and UI-03 `3020/8020` were not stopped or modified.
- API startup: Python already installed in the AUTH checkpoint venv; script
  `api/scripts/run_local_checkpoint.py --database <absolute-isolated-path> --origin
  http://127.0.0.1:3022 --port 8022 --demo-seed`, empty `OPENAI_API_KEY`, no key-file.
- Next: variables `HOSO_AUTH_PROVIDER=local`, `HOSO_PUBLIC_ORIGIN=http://127.0.0.1:3022`,
  `HOSO_API_URL=http://127.0.0.1:8022`, empty `HOSO_VINCENT_API_URL`;
  `node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3022` from web.

## Limits and next handoff

No live model/provider/Vincent call, PostgreSQL migration, public deployment,
ACCESS-01 voice integration, legal approval or officially filled PDF is established.
Originals and the download lock are preserved. Profile copying is deterministic,
but typed messages may reach AI/retrieval once services are connected; the privacy
information states this explicitly.

No promise of encryption at rest, certification, deletion or universal protection.
Legacy Clerk screens and their older demos outside the LOCAL journey are not
converted by this checkpoint. Backend responses are not automatically translated,
so there is no evidence of a live bilingual model.

The catalog is absent; rows cannot be reliably classified into document types or
stable alternative groups. Requirements display does not compute a legal decision
on applicability or completeness. Preparation tracking and drafts remain in page
memory, separate from the saved profile.

Next handoff: human review of this exact checkpoint by Kim/manager; no further
implementation or automatic publication started after this report.
