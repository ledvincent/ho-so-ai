<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->

## Shared application ownership

- This is the single Next application. Reuse Clerk and `docs/application-contract.md`; do not create a second portal package or identity scheme.
- Read `docs/team/portal-handoff.md` before portal work. Keep forms, shared auth/proxies, dependencies and contract changes coordinated with the scaffold owner.
- `lib/profile.generated.ts` comes from the FastAPI profile model. Regenerate it through `api/scripts/export_profile_contract.py` instead of editing it manually.
- Keep owner checks server-side. A client-provided user ID, fake account, or synthetic fixture cannot establish authentication.
