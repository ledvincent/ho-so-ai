/** Synthetic transport/lifecycle tests. No live Clerk session or network is used. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { EMPTY_PROFILE, type ProfileFields } from '../../lib/contracts';
import { editDraft, newDraft, prefillDraft } from '../../lib/forms/draft';
import { ProfileController, PROFILE_MESSAGES, problemForStatus, readProfile } from './profile-state';

const record = (name = 'Synthetic account A', revision = 1) => ({
  profile_id: 'synthetic-profile-a', revision, fields: { ...EMPTY_PROFILE, full_name: name },
});
const json = (value: unknown, status = 200) => Response.json(value, { status });
test('default browser fetch is not invoked with the profile controller as its receiver', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async function (this: unknown) {
    assert.equal(this instanceof ProfileController, false);
    return json({ detail: { code: 'PROFILE_NOT_FOUND' } }, 404);
  } as typeof fetch;
  try {
    const controller = new ProfileController();
    await controller.load();
    assert.equal(controller.snapshot().phase, 'ready');
    assert.equal(controller.snapshot().revision, 0);
  } finally { globalThis.fetch = original; }
});
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

test('missing own profile enables explicit revision-zero creation; GET never writes', async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const controller = new ProfileController(async (url, init) => {
    calls.push({ url, init });
    return calls.length === 1 ? json({}, 404) : json(record());
  });
  await controller.load();
  assert.equal(controller.snapshot().revision, 0);
  assert.equal(controller.snapshot().saved, false);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].init.method, 'GET');
  controller.edit('full_name', 'Synthetic account A');
  await controller.save();
  assert.equal(calls[1].url, '/api/profile');
  assert.equal(calls[1].init.method, 'PUT');
  assert.deepEqual(JSON.parse(String(calls[1].init.body)), {
    expected_revision: 0, fields: { ...EMPTY_PROFILE, full_name: 'Synthetic account A' },
  });
  assert.equal(controller.snapshot().revision, 1);
  assert.equal(controller.snapshot().saved, true);
});

test('edits stay local until save and requests contain no owner, profile ID or session token', async () => {
  const calls: RequestInit[] = [];
  const controller = new ProfileController(async (_url, init) => {
    calls.push(init);
    return json(record(calls.length === 1 ? 'Synthetic A' : 'Corrected synthetic A', calls.length === 1 ? 5 : 6));
  });
  await controller.load();
  controller.edit('full_name', 'Corrected synthetic A');
  assert.equal(calls.length, 1);
  assert.equal(controller.snapshot().dirty, true);
  await controller.save();
  assert.deepEqual(Object.keys(JSON.parse(String(calls[1].body))).sort(), ['expected_revision', 'fields']);
  assert.equal(JSON.parse(String(calls[1].body)).expected_revision, 5);
  assert.equal(calls[1].credentials, 'same-origin');
  assert.equal(calls[1].cache, 'no-store');
  assert.equal(new Headers(calls[1].headers).has('Authorization'), false);
  assert.equal(controller.snapshot().dirty, false);
});

test('parallel save clicks send only one write and keep an immutable submission snapshot', async () => {
  const pending = deferred<Response>();
  const calls: RequestInit[] = [];
  const controller = new ProfileController(async (_url, init) => {
    calls.push(init);
    return calls.length === 1 ? json(record()) : pending.promise;
  });
  await controller.load();
  controller.edit('full_name', 'First submitted value');
  const first = controller.save();
  controller.edit('full_name', 'Later edit while saving');
  await controller.save();
  assert.equal(calls.length, 2);
  assert.equal(JSON.parse(String(calls[1].body)).fields.full_name, 'First submitted value');
  pending.resolve(json(record('First submitted value', 2)));
  await first;
  assert.equal(controller.snapshot().fields.full_name, 'First submitted value');
});

test('stale revision preserves unsaved draft and requires a reload before another write', async () => {
  let calls = 0;
  const controller = new ProfileController(async () => {
    calls += 1;
    return calls === 1 ? json(record()) : calls === 2 ? json({ detail: 'Do not show upstream text' }, 409) : json(record('New server value', 2));
  });
  await controller.load();
  controller.edit('full_name', 'Unsaved synthetic change');
  await controller.save();
  assert.equal(controller.snapshot().problem, 'conflict');
  assert.equal(controller.snapshot().fields.full_name, 'Unsaved synthetic change');
  assert.equal(controller.snapshot().saved, false);
  await controller.save();
  assert.equal(calls, 2);
  await controller.load();
  assert.equal(controller.snapshot().fields.full_name, 'New server value');
  assert.equal(controller.snapshot().revision, 2);
  assert.equal(controller.snapshot().dirty, false);
});

test('401 on save clears all prior profile values and revision', async () => {
  let calls = 0;
  const controller = new ProfileController(async () => ++calls === 1 ? json(record()) : json({}, 401));
  await controller.load();
  controller.edit('full_name', 'Unsaved value');
  await controller.save();
  assert.deepEqual(controller.snapshot().fields, EMPTY_PROFILE);
  assert.equal(controller.snapshot().revision, null);
  assert.equal(controller.snapshot().problem, 'signed-out');
  assert.equal(controller.snapshot().dirty, false);
});

test('reset aborts requests and ignores a late response after logout', async () => {
  const pending = deferred<Response>();
  let signal: AbortSignal | null | undefined;
  const controller = new ProfileController(async (_url, init) => { signal = init.signal; return pending.promise; });
  const loading = controller.load();
  controller.reset();
  assert.equal(signal?.aborted, true);
  pending.resolve(json(record()));
  await loading;
  assert.deepEqual(controller.snapshot().fields, EMPTY_PROFILE);
  assert.equal(controller.snapshot().revision, null);
  assert.equal(controller.snapshot().phase, 'idle');
});

test('a new session cannot receive data or save acknowledgments from the previous controller', async () => {
  const pending = deferred<Response>();
  let calls = 0;
  const a = new ProfileController(async () => ++calls === 1 ? json(record()) : pending.promise);
  await a.load();
  a.edit('full_name', 'Unsaved account A');
  const saving = a.save();
  a.reset();
  const b = new ProfileController(async () => json(record('Synthetic account B', 4)));
  await b.load();
  pending.resolve(json(record('Unsaved account A', 2)));
  await saving;
  assert.deepEqual(a.snapshot().fields, EMPTY_PROFILE);
  assert.equal(a.snapshot().saved, false);
  assert.equal(b.snapshot().fields.full_name, 'Synthetic account B');
  assert.equal(b.snapshot().revision, 4);
});

test('older load responses cannot overwrite a newer reload', async () => {
  const old = deferred<Response>();
  let calls = 0;
  const controller = new ProfileController(async () => ++calls === 1 ? old.promise : json(record('Current synthetic value', 3)));
  const first = controller.load();
  await controller.load();
  old.resolve(json(record('Old synthetic value', 1)));
  await first;
  assert.equal(controller.snapshot().fields.full_name, 'Current synthetic value');
  assert.equal(controller.snapshot().revision, 3);
});

test('501 and 503 never simulate successful storage and preserve unsaved edits after failed save', async () => {
  for (const status of [501, 503]) {
    const unconfigured = new ProfileController(async () => json({ detail: 'Sensitive upstream content' }, status));
    await unconfigured.load();
    assert.equal(unconfigured.snapshot().phase, 'blocked');
    assert.equal(unconfigured.snapshot().revision, null);
    assert.equal(unconfigured.snapshot().saved, false);
    let calls = 0;
    const controller = new ProfileController(async () => ++calls === 1 ? json(record()) : json({}, status));
    await controller.load();
    controller.edit('address', 'Synthetic draft address');
    await controller.save();
    assert.equal(controller.snapshot().saved, false);
    assert.equal(controller.snapshot().dirty, true);
    assert.equal(controller.snapshot().fields.address, 'Synthetic draft address');
    assert.equal(controller.snapshot().problem, status === 501 ? 'not-implemented' : 'unavailable');
  }
});

test('malformed and non-advancing successful responses cannot report a save', async () => {
  for (const bad of [{}, record('Stale response', 1), { ...record(), fields: { full_name: 'Partial response' } }]) {
    let calls = 0;
    const controller = new ProfileController(async () => ++calls === 1 ? json(record()) : json(bad));
    await controller.load();
    controller.edit('full_name', 'Unconfirmed change');
    await controller.save();
    assert.equal(controller.snapshot().saved, false);
    assert.equal(controller.snapshot().problem, 'unavailable');
    assert.equal(controller.snapshot().fields.full_name, 'Unconfirmed change');
  }
});

test('status messages are static and do not display error payloads', () => {
  for (const status of [401, 403, 404, 409, 413, 422, 501, 503, 500]) {
    assert.equal(typeof PROFILE_MESSAGES[problemForStatus(status)], 'string');
  }
  assert.equal(problemForStatus(503), 'unavailable');
  assert.equal(problemForStatus(422), 'invalid');
});

test('only the six generated fields cross the response boundary and form edits do not change saved profile', () => {
  const parsed = readProfile({ ...record(), fields: { ...record().fields, unexpected_personal_value: 'Do not copy' } });
  assert.deepEqual(Object.keys(parsed.fields).sort(), Object.keys(EMPTY_PROFILE).sort());
  const form = prefillDraft(newDraft(), parsed.fields);
  const edited = editDraft(form, 'full_name', 'Separate synthetic form correction');
  assert.equal(parsed.fields.full_name, 'Synthetic account A');
  assert.equal(edited.values.full_name, 'Separate synthetic form correction');
  assert.notEqual(form.values, parsed.fields);
  assert.throws(() => readProfile({ ...record(), fields: { ...EMPTY_PROFILE, full_name: 123 } as unknown as ProfileFields }));
});
