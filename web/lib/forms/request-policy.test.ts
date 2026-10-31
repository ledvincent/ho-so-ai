import test from 'node:test';
import assert from 'node:assert/strict';
import { isAllowedMutation } from '../request-policy';

const request = (origin: string, contentType = 'application/json') => new Request('http://localhost:3000/api/profile', { headers: { Origin: origin, 'Content-Type': contentType } });
test('configured public origin accepts a valid browser even when the internal request URL differs', () => {
  assert.equal(isAllowedMutation(request('http://127.0.0.1:3000'), 'http://127.0.0.1:3000'), true);
});
test('a matching internal host cannot authorize a foreign browser origin', () => {
  assert.equal(isAllowedMutation(request('http://localhost:3000'), 'http://127.0.0.1:3000'), false);
  assert.equal(isAllowedMutation(request('https://untrusted.example'), 'http://127.0.0.1:3000'), false);
  assert.equal(isAllowedMutation(request('null'), 'http://127.0.0.1:3000'), false);
});
test('portal port must match its configured canonical origin', () => {
  assert.equal(isAllowedMutation(request('http://127.0.0.1:3001'), 'http://127.0.0.1:3001'), true);
  assert.equal(isAllowedMutation(request('http://127.0.0.1:3001'), 'http://127.0.0.1:3000'), false);
});
test('only JSON and a valid exact origin configuration are accepted', () => {
  assert.equal(isAllowedMutation(request('https://app.example', 'application/json; charset=utf-8'), 'https://app.example'), true);
  assert.equal(isAllowedMutation(request('https://app.example', 'text/plain'), 'https://app.example'), false);
  for (const invalid of ['', '*', 'file:///tmp', 'https://app.example/path', 'https://app.example/']) assert.equal(isAllowedMutation(request('https://app.example'), invalid), false);
});
