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
    console.log(`Disposable engine PostgreSQL version: ${(await db.query('SHOW server_version')).rows[0].server_version}`);
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

// All DDL/grants below exist only in a fresh in-memory engine per scenario.
const forbiddenGrants = [
  ['marker table INSERT', 'identity_namespace', 'INSERT'],
  ['marker column INSERT', 'identity_namespace', 'INSERT (issuer)'],
  ['marker table UPDATE', 'identity_namespace', 'UPDATE'],
  ['marker column UPDATE', 'identity_namespace', 'UPDATE (issuer)'],
  ['marker DELETE', 'identity_namespace', 'DELETE'],
  ['marker TRUNCATE', 'identity_namespace', 'TRUNCATE'],
  ['marker TRIGGER', 'identity_namespace', 'TRIGGER'],
  ['profile owner UPDATE', 'profiles', 'UPDATE (owner_subject)'],
  ['profile ID UPDATE', 'profiles', 'UPDATE (profile_id)'],
  ['profile DELETE', 'profiles', 'DELETE'],
  ['profile TRUNCATE', 'profiles', 'TRUNCATE'],
  ['profile TRIGGER', 'profiles', 'TRIGGER'],
];
for (const mode of ['direct', 'inherited', 'set-only']) {
  for (const [name, table, privilege] of forbiddenGrants) {
    test(`guard rejects ${name} through ${mode} grants`, async () => {
      const recipient = mode === 'direct' ? 'auth01_synthetic_login' : 'synthetic_mutator';
      const role = mode === 'direct' ? '' : `
        CREATE ROLE synthetic_mutator;
        GRANT synthetic_mutator TO auth01_synthetic_login
          WITH INHERIT ${mode === 'inherited' ? 'TRUE' : 'FALSE'}, SET TRUE;
      `;
      const db = await fixture(`${role} GRANT ${privilege} ON hoso_portal.${table} TO ${recipient};`);
      try {
        if (mode === 'set-only') {
          const reach = (await db.query(`SELECT
            pg_has_role(session_user, 'synthetic_mutator', 'MEMBER') AS member,
            pg_has_role(session_user, 'synthetic_mutator', 'USAGE') AS inherited,
            pg_has_role(session_user, 'synthetic_mutator', 'SET') AS switchable
          `)).rows[0];
          assert.deepEqual(reach, { member: true, inherited: false, switchable: true });
        }
        if (name === 'marker column INSERT' || name === 'marker column UPDATE') {
          const permission = name.endsWith('INSERT') ? 'INSERT' : 'UPDATE';
          const acl = (await db.query(`SELECT
            has_table_privilege($1, 'hoso_portal.identity_namespace', $2) AS whole_table,
            has_any_column_privilege($1, 'hoso_portal.identity_namespace', $2) AS any_column
          `, [recipient, permission])).rows[0];
          assert.deepEqual(acl, { whole_table: false, any_column: true });
        }
        assert.equal(await allowed(db), false);
      } finally { await db.close(); }
    });
  }
}

for (const [name, table, privilege] of [
  ['marker UPDATE', 'identity_namespace', 'UPDATE (issuer)'],
  ['profile TRUNCATE', 'profiles', 'TRUNCATE'],
]) {
  test(`mixed SET-then-inherit chain cannot hide ${name}`, async () => {
    const db = await fixture(`
      CREATE ROLE synthetic_parent; CREATE ROLE synthetic_mutator;
      GRANT synthetic_parent TO auth01_synthetic_login WITH INHERIT FALSE, SET TRUE;
      GRANT synthetic_mutator TO synthetic_parent WITH INHERIT TRUE, SET FALSE;
      GRANT ${privilege} ON hoso_portal.${table} TO synthetic_mutator;
    `);
    try {
      const reach = (await db.query(`SELECT
        pg_has_role(session_user, 'synthetic_mutator', 'MEMBER') AS member,
        pg_has_role(session_user, 'synthetic_mutator', 'USAGE') AS inherited,
        pg_has_role(session_user, 'synthetic_mutator', 'SET') AS switchable
      `)).rows[0];
      assert.deepEqual(reach, { member: true, inherited: false, switchable: false });
      assert.equal(await allowed(db), false);
    } finally { await db.close(); }
  });
}

for (const membership of ['INHERIT TRUE, SET FALSE', 'INHERIT FALSE, SET TRUE']) {
  test(`safe custom role passes with ${membership}`, async () => {
    const db = await fixture(`
      CREATE ROLE synthetic_safe;
      GRANT SELECT ON hoso_portal.identity_namespace TO synthetic_safe;
      GRANT UPDATE(full_name) ON hoso_portal.profiles TO synthetic_safe;
      GRANT synthetic_safe TO auth01_synthetic_login WITH ${membership};
    `);
    try { assert.equal(await allowed(db), true); } finally { await db.close(); }
  });
}

test('unsafe dormant membership is conservatively rejected too', async () => {
  const db = await fixture(`
    CREATE ROLE synthetic_dormant;
    GRANT TRUNCATE ON hoso_portal.profiles TO synthetic_dormant;
    GRANT synthetic_dormant TO auth01_synthetic_login WITH INHERIT FALSE, SET FALSE;
  `);
  try { assert.equal(await allowed(db), false); } finally { await db.close(); }
});

test('PUBLIC marker mutation grant cannot evade the guard', async () => {
  const db = await fixture('GRANT UPDATE (issuer) ON hoso_portal.identity_namespace TO PUBLIC;');
  try { assert.equal(await allowed(db), false); } finally { await db.close(); }
});
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
