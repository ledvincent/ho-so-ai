# UI-02 hosting assessment — read-only, 31 October 2026

Recommendation: use a Node web service for Next.js and a Python private service
for the application API, in the same Render region/workspace. Retain the current
frameworks. For the local-auth database, preserve the scaffold owner's delivered
storage contract: SQLite requires a paid persistent disk and a single API
instance; use managed PostgreSQL only if that owner supplies and verifies its
adapter/migration. This is a proposed deployment, not a deployed jury link.

## What was inspected

- Existing Site `appgprj_6ae563e876f48191bead979e185909d3`: active branding Site,
  published version 7, source `9905bc008f0f373eed9ba2cb8e7c3aa12f0ce6b9`.
  Access currently allows only the owner; it is not an open jury link.
- Its retained `.openai/hosting.json` declares `static.directory=dist`. The
  published archive has 11 files. No source credentials, environment values,
  database rows or access settings were changed for this assessment.
- This application uses Next 16.4.3 / React 19.3.1 and server routes/proxies.
  The Python API depends on FastAPI, PyMuPDF, SQLAlchemy and psycopg. Current
  PDF generation requires native Python dependencies, font files and exact
  template assets. It cannot be replaced with a static export while retaining
  authenticated server behavior.

## Sites suitability for this exact application

The installed Sites skill documents hosted server code on Cloudflare Workers,
128 MB per isolate, HTTP external connections and no raw TCP. Its supported
server starter is Vinext with Sites build integration, D1/R2 storage and Sites
identity. The existing branding Site is static.

Cloudflare documents adapters for Next.js on Workers, including Vinext. That
does not establish compatibility of this application's native Python/PDF stack,
local database sessions, PostgreSQL connections or independent username/password
identity with Sites. This repository currently has neither that adapter nor
Sites bindings/build integration. No compatibility build or deployment was run.

Therefore this app cannot be published unchanged by uploading the branding
Site's `dist/`. A Sites implementation would require a separate reviewed
architecture/adaptation and externally hosted compatible services. Such a
conversion is outside this checkpoint. No static imitation was published.

References: installed Sites `SKILL.md`, `references/identity-and-secrets.md`,
`references/storage.md`; [Cloudflare Next.js guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/).

## Concrete deployment work still required

1. Review the delivered AUTH-02/CHAT-01 integration and its database/provider
   acceptance. Provision jury accounts securely; never expose synthetic
   `admin/admin`, local database files or API credentials.
2. Provision the two services, private API hostname and durable storage.
   Render's default filesystem is ephemeral. Paid disk-backed services have
   scaling/deployment constraints, so a SQLite demo must remain single-instance.
3. Build the Next package with its pinned dependencies. Its package start script
   binds loopback; hosted launch must explicitly bind `0.0.0.0` and `$PORT`.
   Start FastAPI similarly on its assigned interface/port.
4. Configure the exact HTTPS public origin, private API URL, server-only OpenAI
   key and signing/session settings using host secrets. Check secure cookies,
   mutation origin checks, expiry, logout and direct URL/API denial on HTTPS.
5. Bundle immutable NA5 workflow/PDF assets and required fonts. Keep the
   human-review/download lock. Review missing backend workflow/research adapters
   separately rather than claiming the local HTML overlay is a generated PDF.
6. Verify a fictional end-to-end journey on the hosted URL, owner isolation,
   restart persistence, stale responses and mobile composer/keyboard behavior.
   Set account/access policy for the jury explicitly before sharing the link.

No hosting account, service, database, credentials, DNS, access policy, framework
or deployment configuration was created or changed during this assessment.

Official references checked on 31 October 2026:

- [Next.js on Render](https://render.com/docs/deploy-nextjs-app): server-side
  applications use a Node web service.
- [FastAPI on Render](https://render.com/docs/deploy-fastapi): Python service
  and Uvicorn launch support.
- [Render private network](https://render.com/docs/private-network): services
  in the same region/workspace communicate on private hostnames; free web
  services cannot receive private-network requests.
- [Render persistent disks](https://render.com/docs/disks): paid services,
  persistent mount paths and filesystem/scaling limitations.
