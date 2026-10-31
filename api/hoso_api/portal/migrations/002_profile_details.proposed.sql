-- REVIEW PROPOSAL ONLY. No automatic runner or shared/live execution authorized.
-- Additive extension on the SAME owner-bound profile row and revision.
-- A separate provisioner reviews/applies this after 001; never the app login.
BEGIN;
ALTER TABLE hoso_portal.profiles
  ADD COLUMN details_json jsonb NOT NULL DEFAULT '{}'::jsonb
  CHECK (jsonb_typeof(details_json) = 'object');
GRANT UPDATE (details_json) ON hoso_portal.profiles TO hoso_portal_runtime;
-- Existing SELECT/INSERT grants and owner RLS policy remain unchanged.
-- No new identity, schema privileges, owner mutation, DELETE or role grants.
COMMIT;
