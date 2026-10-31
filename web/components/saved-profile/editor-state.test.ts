import test from 'node:test';
import assert from 'node:assert/strict';
import { RichProfileController } from './editor-state';
import { ProfileError } from './api';
import { SessionExpired } from '@/components/guided-portal/api';
import { emptyDetails } from './fields';
import type { ProfileV2Response, ProfileV2Update } from '@/lib/profile-v2.generated';
const saved = (revision = 2): ProfileV2Response => ({ schema_version: 'profile.v2', profile_id: 'synthetic-a', revision, details: { ...emptyDetails(), basics: { ...emptyDetails().basics, full_legal_name: 'Fictional A' }, passport: { ...emptyDetails().passport, document_number: '00000123' } }, legacy: { nationality: 'Legacy unspecified meaning' } });

test('editor saves only explicitly, sends complete groups, preserves untouched extensions; cancel never writes', async () => {
  const writes: ProfileV2Update[] = []; let notices = 0;
  const controller = new RichProfileController({ get: async () => saved(), save: async update => { writes.push(update); return { ...saved(3), details: update.details }; } }, () => notices++);
  await controller.load(); controller.edit('contact.phone_number', '0123456789'); assert.equal(writes.length, 0);
  controller.cancel(); assert.equal(controller.snapshot().values['contact.phone_number'], null);
  controller.edit('contact.email', 'fixture@example.test'); await controller.save();
  assert.equal(writes.length, 1); assert.deepEqual(Object.keys(writes[0]).sort(), ['details', 'expected_revision']);
  assert.equal(writes[0].details.passport.document_number, '00000123'); assert.equal(writes[0].details.basics.full_legal_name, 'Fictional A');
  assert.equal(notices, 1); assert.equal(controller.snapshot().saved, true);
});
test('missing profile permits optional creation; failed conflict preserves edits and prevents retry until reload', async () => {
  let writes = 0;
  const controller = new RichProfileController({ get: async () => { throw new ProfileError(404); }, save: async update => { writes++; assert.equal(update.expected_revision, 0); throw new ProfileError(409); } });
  await controller.load(); assert.equal(controller.snapshot().revision, 0);
  controller.edit('basics.full_legal_name', 'Fictional new'); await controller.save();
  assert.equal(controller.snapshot().problem, 409); assert.equal(controller.snapshot().values['basics.full_legal_name'], 'Fictional new');
  await controller.save(); assert.equal(writes, 1);
});
test('401 clears values and late responses after reset cannot restore a prior account', async () => {
  const controller = new RichProfileController({ get: async () => saved(), save: async () => { throw new SessionExpired(); } });
  await controller.load(); controller.edit('basics.occupation', 'Fictional work'); await controller.save();
  assert.equal(controller.snapshot().problem, 401); assert.equal(controller.snapshot().values['basics.full_legal_name'], null);
  let resolve!: (value: ProfileV2Response) => void;
  const pending = new RichProfileController({ get: () => new Promise(done => { resolve = done; }), save: async () => saved() });
  const loading = pending.load(); pending.reset(); resolve(saved()); await loading;
  assert.equal(pending.snapshot().profileId, null); assert.equal(pending.snapshot().values['basics.full_legal_name'], null);
});
test('unavailable save keeps the unsaved editor draft without claiming success', async () => {
  const controller = new RichProfileController({ get: async () => saved(), save: async () => { throw new ProfileError(503); } });
  await controller.load(); controller.edit('basics.occupation', 'Fictional work'); await controller.save();
  assert.equal(controller.snapshot().dirty, true); assert.equal(controller.snapshot().saved, false); assert.equal(controller.snapshot().values['basics.occupation'], 'Fictional work');
});
