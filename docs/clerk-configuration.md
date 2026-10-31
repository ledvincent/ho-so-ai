# Shared Clerk configuration manifest (no secrets)

Status: local development baseline. Kim selected Clerk; no instance identifier,
issuer, publishable key, server secret or public verification key has been supplied.
Do not create a different Clerk application per chat. The portal, forms and Son's
authorization integration must agree on the same development instance and exact issuer.
Live sign-in, logout/revocation and cross-service identity are not verified here.

## Local endpoints

| Component | Forms workstream | Isolated Clerk portal worktree |
| --- | --- | --- |
| Public Next origin | `http://127.0.0.1:3000` | `http://127.0.0.1:3001` |
| Server-only FastAPI origin | `http://127.0.0.1:8000` | `http://127.0.0.1:8001` |
| Browser profile route | `/api/profile` | `/api/profile` |
| API profile route | `/v1/profile` | `/v1/profile` |
| Contract | `app.v1` | Same baseline, not a new schema |

Development authorized parties in both example files are exactly:

```text
http://localhost:3000
http://127.0.0.1:3000
http://localhost:3001
http://127.0.0.1:3001
```

These are local development origins only. Production needs its own explicit HTTPS
origins and the same issuer/instance agreement. The browser calls the same-origin
Next proxies; `HOSO_API_URL` is server-only. API CORS defaults do not make a private
route public or replace token/owner checks.

## Variables and ownership

| Location | Variable | Meaning / current value |
| --- | --- | --- |
| `web/.env.local` | `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Same selected Clerk instance; unset |
| `web/.env.local` | `CLERK_SECRET_KEY` | Server-only Clerk secret; unset, never publish |
| Both local environments | `CLERK_AUTHORIZED_PARTIES` | Four exact development origins above |
| `web/.env.local` | `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | `/sign-in` |
| `web/.env.local` | `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | `/sign-up` |
| `web/.env.local` | `HOSO_API_URL` | Forms `http://127.0.0.1:8000`; portal `http://127.0.0.1:8001` |
| `web/.env.local` | `HOSO_PUBLIC_ORIGIN` | Forms `http://127.0.0.1:3000`; portal `http://127.0.0.1:3001`; exact canonical origin for mutation checks |
| API environment | `CLERK_ISSUER` | Exact issuer from the agreed instance; unset, do not guess |
| API environment | `CLERK_JWT_KEY` | Public JWT verification PEM for that issuer; unset |
| API environment | `CLERK_AUDIENCE` | Optional expected `aud`; unset means no audience configured |
| API environment | `DATABASE_URL` | Restricted application connection, not provisioning owner; unset |
| API environment | `DEMO_FORMS_ENABLED` | Default false; local synthetic example explicitly true |

The publishable key, server secret and public JWT verification key are distinct.
The API currently verifies session tokens locally with the public PEM plus issuer,
authorized-party and required-claim checks; it does not make a live Clerk key lookup.
Configure rotation and revocation behavior with Son before claiming immediate logout
enforcement. Do not copy configured env files or tokens into the repository, prompts,
handoff or another worktree without a separately agreed local destination.

## Portal setup handoff

1. Confirm the shared development Clerk instance with Kim and Son, then configure
   username/password sign-in in that instance. No custom password database is needed.
2. Supply the values through each worktree's ignored local environment, not Git.
3. Use a separate database/Compose project or explicitly coordinated development
   database and restricted runtime role. The scaffold does not apply a migration.
4. Test live sign-in and one protected API request. Then test two synthetic accounts
   against the actual profile repository before claiming ownership isolation.

Shared auth, profile model, generated types, proxies and dependency locks remain
with the scaffold owner. Follow `team/portal-handoff.md` for writable portal paths.

References: [Clerk Next.js setup](https://clerk.com/docs/nextjs/getting-started/quickstart),
[Clerk Python SDK](https://github.com/clerk/clerk-sdk-python),
[authorized parties](https://clerk.com/docs/guides/development/deployment/production).
