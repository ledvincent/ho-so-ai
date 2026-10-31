import test from 'node:test';
import assert from 'node:assert/strict';
import { identityFrom, isLocalProvider, isPrivatePage, localOrigin, validSessionToken } from './local-auth-policy';

function withEnvironment(values: Record<string, string | undefined>, action: () => void) {
  const previous = Object.fromEntries(Object.keys(values).map((key) => [key, process.env[key]]));
  try {
    for (const [key, value] of Object.entries(values)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    action();
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

function identity() {
  return { user: { id: 'synthetic-account-a', username: 'synthetic_a', identity_provider: 'local' }, expires_at: Math.floor(Date.now() / 1000) + 120 };
}

test('the browser identity DTO copies only its allowed fields and drops credentials', () => {
  const expected = identity();
  const upstream = { ...expected, session_token: 'private-session-marker', password: 'private-password-marker',
    user: { ...expected.user, token: 'private-nested-marker', password_hash: 'private-hash-marker', role: 'admin' } };
  const result = identityFrom(upstream);
  assert.deepEqual(result, expected);
  assert.equal(JSON.stringify(result).includes('private-'), false);
  upstream.user.username = 'changed_after_validation';
  assert.equal(result?.user.username, 'synthetic_a');
});

test('expired, malformed and non-local identities do not establish a browser session', () => {
  const good = identity();
  for (const value of [null, [], {}, { ...good, user: null },
    { ...good, expires_at: Math.floor(Date.now() / 1000) - 1 },
    { ...good, expires_at: '9999999999' }, { ...good, expires_at: Infinity },
    { ...good, expires_at: good.expires_at + 0.5 },
    { ...good, user: { ...good.user, identity_provider: 'clerk' } },
    { ...good, user: { ...good.user, id: '' } },
    { ...good, user: { ...good.user, id: 'x'.repeat(257) } },
    { ...good, user: { ...good.user, username: '<script>' } },
    { ...good, user: { ...good.user, username: 'name with spaces' } }]) {
    assert.equal(identityFrom(value), null);
  }
});

test('opaque cookie values accept only bounded URL-safe tokens', () => {
  assert.equal(validSessionToken('a'.repeat(40)), true);
  assert.equal(validSessionToken('_a-9'.repeat(64)), true);
  for (const value of [undefined, null, 123, '', 'a'.repeat(39), 'a'.repeat(257),
    'a'.repeat(40) + ';Path=/', 'a'.repeat(40) + '\n', 'é'.repeat(40), 'a'.repeat(40) + '=']) {
    assert.equal(validSessionToken(value), false);
  }
});

test('protected page prefixes include nested and dotted paths', () => {
  for (const path of ['/portal', '/portal/settings', '/workspace', '/workspace/secret.txt',
    '/chat', '/chat/session.1', '/forms', '/forms/demo', '/forms/1.001146',
    '/research', '/documents/private.pdf', '/demo', '/demo/workspace', '/demo/guided']) {
    assert.equal(isPrivatePage(path), true, path);
  }
});

test('public entry paths and similarly named prefixes are not treated as private pages', () => {
  for (const path of ['/', '/login', '/demo/login', '/sign-in', '/sign-in/sso-callback',
    '/workspace-public', '/portals', '/chatty', '/forms-public', '/research-public', '/demoish']) {
    assert.equal(isPrivatePage(path), false, path);
  }
});

test('local origin accepts only canonical loopback HTTP(S) origins', () => {
  for (const origin of ['http://127.0.0.1:3015', 'http://localhost:3015', 'https://localhost:3015', 'http://[::1]:3015']) {
    withEnvironment({ HOSO_PUBLIC_ORIGIN: origin }, () => assert.equal(localOrigin().origin, origin));
  }
});

test('local origin rejects remote, ambiguous and malformed configuration', () => {
  for (const origin of [undefined, '', 'not-a-url', 'https://example.invalid', 'http://localhost.evil.invalid:3015',
    'http://127.0.0.1.evil.invalid', 'ftp://localhost:3015', 'http://user:password@localhost:3015',
    'http://localhost:3015/', 'http://localhost:3015/path', 'http://localhost:3015?next=private',
    'http://localhost:3015#fragment']) {
    withEnvironment({ HOSO_PUBLIC_ORIGIN: origin }, () => assert.throws(() => localOrigin()));
  }
});

test('LOCAL is an explicit provider choice and invalid values never enable it', () => {
  withEnvironment({ HOSO_AUTH_PROVIDER: 'local' }, () => assert.equal(isLocalProvider(), true));
  for (const provider of [undefined, '', 'clerk', 'LOCAL', ' local', 'local ', 'unknown']) {
    withEnvironment({ HOSO_AUTH_PROVIDER: provider }, () => assert.equal(isLocalProvider(), false));
  }
});
