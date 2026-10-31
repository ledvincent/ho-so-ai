/** Synthetic page events. This does not establish browser bfcache behavior. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { EMPTY_PROFILE } from '../../lib/contracts';
import { listenForProfilePageLifecycle } from './page-lifecycle';
import { ProfileController } from './profile-state';

function restoredPage(persisted: boolean) {
  return Object.assign(new Event('pageshow'), { persisted });
}

test('pagehide clears, persisted pageshow clears before reload, and cleanup removes both listeners', () => {
  const target = new EventTarget();
  const calls: string[] = [];
  const cleanup = listenForProfilePageLifecycle(target, () => calls.push('clear'), () => calls.push('reload'));
  target.dispatchEvent(new Event('visibilitychange'));
  target.dispatchEvent(restoredPage(false));
  assert.deepEqual(calls, []);
  target.dispatchEvent(new Event('pagehide'));
  assert.deepEqual(calls, ['clear']);
  target.dispatchEvent(restoredPage(true));
  assert.deepEqual(calls, ['clear', 'clear', 'reload']);
  cleanup();
  target.dispatchEvent(new Event('pagehide'));
  target.dispatchEvent(restoredPage(true));
  assert.deepEqual(calls, ['clear', 'clear', 'reload']);
});

test('pagehide erases a loaded draft and prevents a pending save from restoring it; restoration rechecks API', async () => {
  const target = new EventTarget();
  let completeSave!: (response: Response) => void;
  const pendingSave = new Promise<Response>((resolve) => { completeSave = resolve; });
  let calls = 0;
  const controller = new ProfileController(async () => {
    calls += 1;
    if (calls === 1) return Response.json({ profile_id: 'synthetic-profile-a', revision: 1, fields: { ...EMPTY_PROFILE, full_name: 'Synthetic A' } });
    if (calls === 2) return pendingSave;
    return Response.json({}, { status: 401 });
  });
  let reloaded: Promise<void> | undefined;
  const cleanup = listenForProfilePageLifecycle(target, () => controller.reset(), () => { reloaded = controller.load(); });
  await controller.load();
  controller.edit('address', 'Unsaved synthetic address');
  const saving = controller.save();
  target.dispatchEvent(new Event('pagehide'));
  assert.deepEqual(controller.snapshot().fields, EMPTY_PROFILE);
  assert.equal(controller.snapshot().revision, null);
  completeSave(Response.json({ profile_id: 'synthetic-profile-a', revision: 2, fields: { ...EMPTY_PROFILE, full_name: 'Synthetic A' } }));
  await saving;
  assert.deepEqual(controller.snapshot().fields, EMPTY_PROFILE);
  assert.equal(controller.snapshot().saved, false);
  target.dispatchEvent(restoredPage(true));
  assert.deepEqual(controller.snapshot().fields, EMPTY_PROFILE);
  await reloaded;
  assert.equal(calls, 3);
  assert.equal(controller.snapshot().problem, 'signed-out');
  assert.deepEqual(controller.snapshot().fields, EMPTY_PROFILE);
  cleanup();
});
