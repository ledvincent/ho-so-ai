import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyValues } from '@/components/na5-demo/model';
import { applyRows, prepareRows, selectRow, type PrefillBinding, type PrefillSource } from './prefill-model';

const binding: PrefillBinding = { session: 'account-a:session-1', document: 'code:form:schema:epoch-1', draftRevision: 4, profileId: 'profile-a', profileRevision: 2 };
const row = (id: string, target: string, value: string, requiresDocument = false) => ({ id, target, value, requiresDocument, sourceLabel: id, sourceValue: value });
const source = (rows: PrefillSource['rows']): PrefillSource => ({ profileId: 'profile-a', revision: 2, rows, warnings: [] });
test('contact proposals are alternatives for one target; user can select combined text or none', () => {
  const rows = prepareRows(source([row('phone', 'contact', '0123456789'), row('email', 'contact', 'fixture@example.test'), row('both', 'contact', '0123456789 / fixture@example.test')]), emptyValues());
  assert.deepEqual(rows.filter(item => item.selected).map(item => item.id), ['phone']);
  const combined = selectRow(rows, 'both', true);
  assert.deepEqual(combined.filter(item => item.selected).map(item => item.id), ['both']);
  assert.equal(applyRows(combined, emptyValues(), binding, binding).contact, '0123456789 / fixture@example.test');
  assert.equal(selectRow(combined, 'both', false).some(item => item.selected), false);
  assert.throws(() => applyRows(rows.map(item => ({ ...item, selected: true })), emptyValues(), binding, binding));
});
test('typed draft answers stay locked even when equal to the saved value', () => {
  const draft = { ...emptyValues(), applicant_full_name: 'TYPED NAME' };
  const rows = prepareRows(source([row('name', 'applicant_full_name', 'TYPED NAME'), row('dob', 'birth_date', '1990-02-01')]), draft);
  assert.equal(rows[0].locked, true); assert.equal(rows[0].selected, false);
  const next = applyRows(rows, draft, binding, binding);
  assert.equal(next.applicant_full_name, 'TYPED NAME'); assert.equal(next.birth_date, '1990-02-01');
  assert.equal(draft.birth_date, undefined);
  assert.throws(() => applyRows(rows.map(item => ({ ...item, selected: true })), draft, binding, binding));
});
test('passport copies require separate intended-document confirmation and preserve leading zeroes', () => {
  const rows = prepareRows(source([row('passport', 'passport_number', '000012345', true)]), emptyValues());
  assert.equal(rows[0].selected, false);
  rows[0].selected = true;
  assert.throws(() => applyRows(rows, emptyValues(), binding, binding));
  assert.equal(applyRows(rows, emptyValues(), binding, binding, true).passport_number, '000012345');
});
test('every account, document, draft and profile binding must match before apply', () => {
  const rows = prepareRows(source([row('name', 'applicant_full_name', 'Fictional Name')]), emptyValues());
  for (const key of Object.keys(binding) as (keyof PrefillBinding)[]) {
    const changed = { ...binding, [key]: typeof binding[key] === 'number' ? Number(binding[key]) + 1 : `${binding[key]}-changed` };
    assert.throws(() => applyRows(rows, emptyValues(), binding, changed));
  }
  assert.equal(applyRows(rows, emptyValues(), binding, binding).applicant_full_name, 'FICTIONAL NAME');
});
test('unexpected/duplicate targets and invalid or overlong proposals never copy', () => {
  assert.throws(() => prepareRows(source([row('sponsor', 'host_name', 'Fictional')]), emptyValues()));
  assert.throws(() => prepareRows(source([row('name', 'applicant_full_name', 'A'), row('name2', 'applicant_full_name', 'B')]), emptyValues()));
  const rows = prepareRows(source([row('name', 'applicant_full_name', 'X'.repeat(101)), row('date', 'birth_date', '2026-02-30')]), emptyValues());
  assert.equal(rows.some(item => item.selected), false);
  assert.throws(() => applyRows(rows.map(item => ({ ...item, selected: true })), emptyValues(), binding, binding));
});
