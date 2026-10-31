/** Optional disposable PostgreSQL-engine checks (PGlite 0.3.16).
 * No server, credential, live migration, network or persistent data directory.
 * Set AUTH01_PGLITE_MODULE to an explicitly installed PGlite dist/index.js path.
 * This does not exercise SQLAlchemy/psycopg, TLS, multi-connection PostgreSQL
 * concurrency or production route registration. Keep those evidence separate.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const modulePath = process.env.AUTH01_PGLITE_MODULE;
if (!modulePath) throw new Error('Set AUTH01_PGLITE_MODULE explicitly; no dependency is installed automatically.');
const { PGlite } = await import(pathToFileURL(path.resolve(modulePath)).href);
const api = fileURLToPath(new URL('../../', import.meta.url));
const python = process.env.AUTH01_PYTHON ?? path.join(api, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const exported = spawnSync(python, ['-c', [
  'import json',
  'from hoso_api.portal.repository import _READ, _CREATE, _UPDATE',
  'from hoso_api.portal.postgres import _ROLE_CHECK, _NAMESPACE, _CONTEXT',
  'print(json.dumps({k: str(v) for k, v in dict(read=_READ, create=_CREATE, update=_UPDATE, role=_ROLE_CHECK, namespace=_NAMESPACE, context=_CONTEXT).items()}))',
].join('; ')], { cwd: api, encoding: 'utf8' });
if (exported.status !== 0) throw new Error('Could not import repository SQL from the API environment.');
const sql = JSON.parse(exported.stdout);
const migration = await readFile(path.join(api, 'hoso_api/portal/migrations/001_profile.proposed.sql'), 'utf8');
const issuer = 'https://auth01-synthetic.clerk.accounts.dev';

function query(db, name, parameters = {}) {
  const values = [];
  const statement = sql[name].replace(/:([a-z_]+)/g, (_all, key) => {
    assert.ok(Object.hasOwn(parameters, key), `Missing synthetic parameter ${key}`);
    values.push(parameters[key]);
    return `$${values.length}`;
  });
  return db.query(statement, values);
}
function payload(subject, revision = 0) {
  return { subject, profile_id: `synthetic-profile-${subject}`, expected_revision: revision,
    full_name: `Synthetic ${subject}`, date_of_birth: null, nationality: null,
    address: 'Synthetic address', phone_number: null, email: null };
}
async function fixture(extra = '') {
  const db = new PGlite();
  await db.exec(migration);
  await db.query('INSERT INTO hoso_portal.identity_namespace (issuer) VALUES ($1)', [issuer]);
  await db.exec(`
    CREATE ROLE auth01_synthetic_login LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
    GRANT hoso_portal_runtime TO auth01_synthetic_login;
    ${extra}
    SET SESSION AUTHORIZATION auth01_synthetic_login;
  `);
  const login = (await db.query('SELECT current_user, session_user')).rows[0];
  assert.equal(login.current_user, 'auth01_synthetic_login');
  assert.equal(login.session_user, 'auth01_synthetic_login');
  return db;
}
async function asUser(db, subject, callback) {
  return db.transaction(async (tx) => {
    await query(tx, 'context', { subject });
    return callback(tx);
  });
}
async function allowed(db) {
  return Object.values((await query(db, 'role')).rows[0])[0];
}

test('restricted login passes guard; exact repository SQL isolates A/B and revision conflicts', async () => {
  const db = await fixture();
  try {
    assert.equal(await allowed(db), true);
    assert.equal((await query(db, 'namespace')).rows[0].issuer, issuer);
    await asUser(db, 'A', async (tx) => {
      assert.equal((await query(tx, 'create', payload('A'))).rows[0].revision, 1);
      assert.equal((await query(tx, 'create', payload('A'))).rows.length, 0);
    });
    await asUser(db, 'B', async (tx) => {
      assert.equal((await query(tx, 'read', { subject: 'A' })).rows.length, 0);
      assert.equal((await query(tx, 'update', payload('A', 1))).rows.length, 0);
      assert.equal((await query(tx, 'create', payload('B'))).rows[0].revision, 1);
    });
    await asUser(db, 'A', async (tx) => {
      assert.equal((await query(tx, 'read', { subject: 'B' })).rows.length, 0);
      assert.equal((await query(tx, 'update', payload('B', 1))).rows.length, 0);
      assert.equal((await query(tx, 'update', payload('A', 1))).rows[0].revision, 2);
      assert.equal((await query(tx, 'update', payload('A', 1))).rows.length, 0);
    });
  } finally { await db.close(); }
});

test('RLS filters direct unscoped reads, blocks forged owner insert and protects identity columns', async () => {
  const db = await fixture();
  try {
    await asUser(db, 'A', (tx) => query(tx, 'create', payload('A')));
    await asUser(db, 'B', (tx) => query(tx, 'create', payload('B')));
    await asUser(db, 'A', async (tx) => {
      const rows = (await tx.query('SELECT owner_subject FROM hoso_portal.profiles')).rows;
      assert.deepEqual(rows, [{ owner_subject: 'A' }]);
    });
    await assert.rejects(asUser(db, 'A', (tx) => query(tx, 'create', payload('C'))), { code: '42501' });
    await assert.rejects(asUser(db, 'A', (tx) => tx.exec("UPDATE hoso_portal.profiles SET owner_subject='C'")), { code: '42501' });
    await assert.rejects(asUser(db, 'A', (tx) => tx.exec("UPDATE hoso_portal.profiles SET profile_id='other'")), { code: '42501' });
    await assert.rejects(db.exec("UPDATE hoso_portal.identity_namespace SET issuer='https://other.invalid'"), { code: '42501' });
  } finally { await db.close(); }
});

test('transaction-local identity clears after commit and rollback; no-context access fails closed', async () => {
  const db = await fixture();
  try {
    await asUser(db, 'A', (tx) => query(tx, 'create', payload('A')));
    assert.deepEqual((await db.query('SELECT * FROM hoso_portal.profiles')).rows, []);
    await assert.rejects(query(db, 'create', payload('C')), { code: '42501' });
    await assert.rejects(asUser(db, 'B', async (tx) => {
      await query(tx, 'create', payload('B'));
      throw new Error('Synthetic rollback');
    }), /Synthetic rollback/);
    assert.deepEqual((await db.query('SELECT * FROM hoso_portal.profiles')).rows, []);
    assert.equal((await asUser(db, 'B', (tx) => query(tx, 'read', { subject: 'B' }))).rows.length, 0);
    assert.equal((await asUser(db, 'A', (tx) => query(tx, 'read', { subject: 'A' }))).rows.length, 1);
  } finally { await db.close(); }
});

for (const role of ['pg_read_all_data', 'pg_write_all_data', 'pg_read_server_files', 'pg_write_server_files', 'pg_execute_server_program']) {
  test(`guard refuses restricted login with indirect ${role} membership`, async () => {
    const db = await fixture(`CREATE ROLE synthetic_extra; GRANT ${role} TO synthetic_extra; GRANT synthetic_extra TO auth01_synthetic_login;`);
    try { assert.equal(await allowed(db), false); } finally { await db.close(); }
  });
}
for (const [name, grant] of [
  ['schema creation', 'GRANT CREATE ON SCHEMA hoso_portal TO auth01_synthetic_login'],
  ['owner column changes', 'GRANT UPDATE(owner_subject) ON hoso_portal.profiles TO auth01_synthetic_login'],
  ['bypassrls', 'ALTER ROLE auth01_synthetic_login BYPASSRLS'],
  ['table ownership membership', 'CREATE ROLE synthetic_owner; ALTER TABLE hoso_portal.profiles OWNER TO synthetic_owner; GRANT synthetic_owner TO auth01_synthetic_login'],
]) {
  test(`guard refuses ${name}`, async () => {
    const db = await fixture(grant + ';');
    try { assert.equal(await allowed(db), false); } finally { await db.close(); }
  });
}
