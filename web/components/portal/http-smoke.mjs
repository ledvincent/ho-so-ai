/** Unconfigured local preview only; no credentials or synthetic sign-in bypass. */
import assert from 'node:assert/strict';

const origin = 'http://127.0.0.1:3001';
for (const [path, status, marker] of [
  ['/portal', 200, 'Đăng nhập chưa sẵn sàng'],
  ['/api/profile', 503, 'AUTH_UNAVAILABLE'],
]) {
  const response = await fetch(origin + path, { redirect: 'error', signal: AbortSignal.timeout(10_000) });
  assert.equal(response.status, status);
  assert.match(response.headers.get('cache-control') ?? '', /no-store/);
  assert.ok((await response.text()).includes(marker));
  console.log(`PASS ${path}: ${status}, no-store, explicit unavailable state`);
}
