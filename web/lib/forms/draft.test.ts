import test from 'node:test';
import assert from 'node:assert/strict';
import { EMPTY_PROFILE } from '../contracts';
import { canDownload, captureRequest, clearDraft, editDraft, isCurrent, newDraft, prefillDraft, validateProfile } from './draft';

test('account prefill copies values; later edits do not mutate the saved account object', () => {
  const account = { ...EMPTY_PROFILE, full_name: 'Synthetic person', address: 'Synthetic address' };
  const draft = prefillDraft(newDraft(), account);
  account.full_name = 'Later external mutation';
  const changed = editDraft(draft, 'address', 'Local correction');
  assert.equal(changed.values.full_name, 'Synthetic person');
  assert.equal(account.address, 'Synthetic address');
});
test('cleared and missing account values replace prior document data', () => {
  const previous = editDraft(newDraft(), 'address', 'Old address');
  const next = prefillDraft(previous, { ...EMPTY_PROFILE, full_name: 'Corrected' });
  assert.equal(next.values.address, null);
  assert.equal(next.values.full_name, 'Corrected');
});
test('prefill copies only declared fields and rejects malformed field values', () => {
  const input = { ...EMPTY_PROFILE, full_name: 'Synthetic', extra_sensitive_field: 'Must not travel' };
  const result = prefillDraft(newDraft(), input);
  assert.equal(Object.hasOwn(result.values, 'extra_sensitive_field'), false);
  assert.throws(() => prefillDraft(newDraft(), { ...EMPTY_PROFILE, full_name: 42 } as never));
});
test('every edit or clear invalidates the preview and acknowledgement', () => {
  const base = { ...newDraft(), acknowledged: true, previewRevision: 1 };
  assert.equal(canDownload(base), true);
  const edited = editDraft(base, 'full_name', 'New');
  assert.equal(canDownload(edited), false);
  const cleared = clearDraft(edited);
  assert.equal(cleared.revision, edited.revision + 1);
  assert.equal(cleared.source, 'manual');
  assert.deepEqual(cleared.values, EMPTY_PROFILE);
});
test('a render gets an immutable snapshot and late responses are rejected after edits', () => {
  const draft = editDraft(newDraft(), 'full_name', 'Nguyễn Văn Mẫu');
  const request = captureRequest(draft);
  assert.throws(() => { request.values.full_name = 'Hidden mutation'; });
  assert.equal(isCurrent(draft, request), true);
  assert.equal(isCurrent(editDraft(draft, 'full_name', 'Corrected'), request), false);
});
test('invalid dates, emails and long values remain present and block export', () => {
  const values = { ...EMPTY_PROFILE, full_name: 'ắ'.repeat(121), date_of_birth: '2026-02-30', email: 'invalid' };
  assert.deepEqual(Object.keys(validateProfile(values)).sort(), ['date_of_birth', 'email', 'full_name']);
  assert.equal(values.full_name.length, 121);
  assert.deepEqual(validateProfile({ ...EMPTY_PROFILE, date_of_birth: '2000-02-29', email: 'demo@example.test' }), {});
});
