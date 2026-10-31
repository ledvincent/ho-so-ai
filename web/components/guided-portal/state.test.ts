import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyValues, example, updateValue } from '@/components/na5-demo/model';
import { changesBetween, checkedValues, nextMissing } from './state';
const valid = { ...example, ...emptyValues() };

test('guided progression follows required NA5 metadata without guessing identity', () => {
  assert.equal(nextMissing(emptyValues())?.id, 'applicant_full_name');
  const values = updateValue(emptyValues(), 'applicant_full_name', 'fictional applicant');
  assert.equal(values.applicant_full_name, 'FICTIONAL APPLICANT');
  assert.notEqual(nextMissing(values)?.id, 'applicant_full_name');
  assert.equal(values.birth_nationality, undefined);
  assert.equal(values.residential_address, undefined);
});

test('UI rejects malformed returned drafts, unknown IDs, impossible dates and workflow changes', () => {
  assert.throws(() => checkedValues({ ...valid, personal_id: 'unmapped' }));
  assert.throws(() => checkedValues({ ...valid, birth_date: '1990-02-31' }));
  assert.throws(() => checkedValues({ ...valid, request_type: 'visa_issuance' }));
  assert.throws(() => checkedValues({ ...valid, passport_number: 123 } as never));
});

test('correction diff includes deleted branch data, and snapshots allow a complete undo', () => {
  const before = checkedValues(valid);
  const snapshot = { ...before };
  const family = updateValue(before, 'host_type', 'family');
  const changes = changesBetween(before, family);
  assert.ok(changes.some(change => change.id === 'host_type' && change.after === 'family'));
  assert.ok(changes.some(change => change.id === 'organisation_name' && change.after === ''));
  assert.deepEqual(before, snapshot);
  assert.equal(snapshot.organisation_name, example.organisation_name);
});

test('appending a user answer preserves local-message translation and change metadata independently of transport history', async () => {
  const { appendUserTurn } = await import('./state');
  const before = [{ role: 'assistant' as const, content: 'Đã áp dụng các mục bạn đã chọn vào bản nháp.', ui: true, changes: [{ id: 'contact', before: '', after: 'fixture@example.test' }] }];
  const after = appendUserTurn(before, 'Fictional answer');
  assert.equal(after[0], before[0]);
  assert.equal(after[0].ui, true);
  assert.equal('changes' in after[0] && after[0].changes[0].after, 'fixture@example.test');
  assert.deepEqual(after.map(({role,content}) => ({role,content})), [{role:'assistant',content:before[0].content},{role:'user',content:'Fictional answer'}]);
});
