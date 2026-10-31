-- REVIEW PROPOSAL ONLY: no automatic runner, no shared/live application authorized.
-- Schema/role names and deployment location must be agreed with the scaffold owner.
-- A provisioner executes DDL; the runtime login must be distinct and nonprivileged.
-- Never run the application as the compose provisioning owner.
BEGIN;
CREATE ROLE hoso_portal_runtime NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
CREATE SCHEMA hoso_portal;
REVOKE ALL ON SCHEMA hoso_portal FROM PUBLIC;

-- Bind this database to ONE configured issuer, without a second account mapping.
CREATE TABLE hoso_portal.identity_namespace (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  issuer text NOT NULL CHECK (length(issuer) BETWEEN 1 AND 2048)
);
-- Provisioner must insert the agreed issuer separately with a bound parameter.
-- Left empty deliberately: the runtime refuses access until that step is reviewed.

CREATE TABLE hoso_portal.profiles (
  owner_subject text PRIMARY KEY CHECK (length(owner_subject) BETWEEN 1 AND 256),
  profile_id text UNIQUE NOT NULL CHECK (length(profile_id) BETWEEN 1 AND 256),
  revision bigint NOT NULL CHECK (revision > 0),
  full_name text CHECK (length(full_name) <= 120),
  date_of_birth text CHECK (length(date_of_birth) <= 10),
  nationality text CHECK (length(nationality) <= 80),
  address text CHECK (length(address) <= 300),
  phone_number text CHECK (length(phone_number) <= 32),
  email text CHECK (length(email) <= 254)
);
ALTER TABLE hoso_portal.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE hoso_portal.profiles FORCE ROW LEVEL SECURITY;
CREATE POLICY profile_owner ON hoso_portal.profiles TO hoso_portal_runtime
  USING (owner_subject = nullif(current_setting('hoso_portal.subject', true), ''))
  WITH CHECK (owner_subject = nullif(current_setting('hoso_portal.subject', true), ''));
REVOKE ALL ON ALL TABLES IN SCHEMA hoso_portal FROM PUBLIC;
GRANT USAGE ON SCHEMA hoso_portal TO hoso_portal_runtime;
GRANT SELECT ON hoso_portal.identity_namespace, hoso_portal.profiles TO hoso_portal_runtime;
GRANT INSERT ON hoso_portal.profiles TO hoso_portal_runtime;
GRANT UPDATE (revision, full_name, date_of_birth, nationality, address, phone_number, email)
  ON hoso_portal.profiles TO hoso_portal_runtime;
-- No DELETE, owner/profile-ID change, DDL, namespace mutation or role administration.
COMMIT;
