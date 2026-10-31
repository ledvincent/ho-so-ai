import test from 'node:test';
import assert from 'node:assert/strict';
import { FormSession } from './state.mjs';

const fields = [{ id: 'demo_name', label: 'Demo name', required: true, maxLength: 40 }, { id: 'demo_note', label: 'Demo note' }];
const make = () => new FormSession(fields);
const load = (state, id = 'synthetic-a', values = { demo_name: 'Synthetic A', demo_note: 'Old note' }) => state.finishLoad(state.beginLoad(id), values);
const artifact = () => ({ blob: new Blob(['Synthetic review copy'], { type: 'text/plain' }), filename: 'review.txt' });
const exportStart = (state) => { state.confirmValues(); return state.beginExport(); };

test('A -> B -> A rejects old A answers even when the session ID matches', () => {
  const state = make();
  const oldA = state.beginLoad('a');
  const oldB = state.beginLoad('b');
  const currentA = state.beginLoad('a');
  assert.equal(state.finishLoad(oldA, { demo_name: 'Old A' }), false);
  assert.equal(state.finishLoad(oldB, { demo_name: 'B' }), false);
  assert.equal(state.finishLoad(currentA, { demo_name: 'Current A' }), true);
  assert.equal(state.snapshot().values.demo_name, 'Current A');
});

test('two loads for the same session cannot complete out of order', () => {
  const state = make();
  const first = state.beginLoad('a');
  const second = state.beginLoad('a');
  state.finishLoad(second, { demo_name: 'Corrected' });
  assert.equal(state.finishLoad(first, { demo_name: 'Old' }), false);
  assert.equal(state.snapshot().values.demo_name, 'Corrected');
});

test('switching sessions immediately removes editor, preview and document state', () => {
  const state = make(); load(state);
  state.finishExport(exportStart(state).token, artifact());
  state.beginLoad('b');
  assert.deepEqual(state.snapshot().values, {});
  assert.equal(state.document(), null);
  assert.equal(state.snapshot().checked, false);
  assert.throws(() => state.edit('demo_name', 'Not loaded'));
});

test('corrected answers replace values, including cleared and omitted fields', () => {
  const state = make(); load(state);
  state.replaceAnswers({ demo_name: 'Corrected', demo_note: '' });
  assert.equal(state.snapshot().values.demo_note, '');
  state.replaceAnswers({ demo_name: 'Latest' });
  assert.equal(state.snapshot().values.demo_note, '');
  assert.equal(state.snapshot().values.demo_name, 'Latest');
});

test('caller mutations cannot change data without a new state revision', () => {
  const state = make();
  const input = { demo_name: 'Initial' }; load(state, 'a', input);
  input.demo_name = 'Mutated';
  const snapshot = state.snapshot();
  assert.equal(snapshot.values.demo_name, 'Initial');
  assert.throws(() => { snapshot.values.demo_name = 'Other'; }, TypeError);
  assert.throws(() => { state.fields[0].label = 'Other'; }, TypeError);
});

test('editing invalidates an existing download and user acknowledgement', () => {
  const state = make(); load(state);
  state.finishExport(exportStart(state).token, artifact());
  state.edit('demo_note', 'Updated');
  assert.equal(state.document(), null);
  assert.equal(state.snapshot().checked, false);
  assert.throws(() => state.beginExport(), /Check the current/);
});

test('revoking acknowledgement invalidates downloads without changing the answer revision', () => {
  const state = make(); load(state);
  state.finishExport(exportStart(state).token, artifact());
  const revision = state.snapshot().revision;
  state.revokeConfirmation();
  assert.equal(state.snapshot().revision, revision);
  assert.equal(state.snapshot().checked, false);
  assert.equal(state.document(), null);
});

test('a delayed export is discarded after editing or an A -> B -> A switch', () => {
  const state = make(); load(state, 'a');
  const first = exportStart(state);
  state.edit('demo_name', 'Changed');
  assert.equal(state.finishExport(first.token, artifact()), false);
  const second = exportStart(state);
  load(state, 'b'); load(state, 'a');
  assert.equal(state.finishExport(second.token, artifact()), false);
  assert.equal(state.document(), null);
});

test('template or mapping version changes invalidate downloads and pending exports', () => {
  const state = make(); load(state);
  const first = exportStart(state);
  state.setTemplateVersion('synthetic-v2');
  assert.equal(state.finishExport(first.token, artifact()), false);
  assert.equal(state.snapshot().checked, false);
  state.finishExport(exportStart(state).token, artifact());
  state.setTemplateVersion('synthetic-v3');
  assert.equal(state.document(), null);
});

test('the export adapter receives the same immutable values as the checked preview', () => {
  const state = make(); load(state);
  state.edit('demo_name', 'Nguyễn Văn Mẫu'); state.confirmValues();
  const preview = state.snapshot();
  const { token, snapshot } = state.beginExport();
  assert.deepEqual(snapshot.values, preview.values);
  assert.equal(snapshot.revision, preview.revision);
  assert.equal(snapshot.templateVersion, preview.templateVersion);
  assert.equal(state.finishExport(token, artifact()), true);
  assert.equal(state.document().revision, preview.revision);
});

test('missing and overflowing values remain visible and block exports without truncation', () => {
  const state = make(); load(state, 'a', {});
  assert.equal(state.snapshot().errors.demo_name, 'This field is required.');
  assert.throws(() => state.confirmValues());
  const long = 'ắ'.repeat(41); state.edit('demo_name', long);
  assert.equal(state.snapshot().values.demo_name, long);
  assert.equal(state.snapshot().valid, false);
  assert.throws(() => state.confirmValues());
});

test('only the latest export attempt can attach its document', () => {
  const state = make(); load(state);
  const first = exportStart(state); const second = state.beginExport();
  assert.equal(state.finishExport(first.token, artifact()), false);
  assert.equal(state.finishExport(second.token, artifact()), true);
});

test('load/export failures are visible, cleared on retry, and cannot affect another session', () => {
  const state = make(); load(state);
  const old = state.beginLoad('b'); const current = state.beginLoad('c');
  assert.equal(state.failLoad(old), false);
  assert.equal(state.failLoad(current), true);
  assert.deepEqual(state.snapshot().values, {});
  assert.ok(state.snapshot().error);
  load(state); const { token } = exportStart(state);
  assert.equal(state.failExport(token), true);
  assert.ok(state.snapshot().error);
  state.beginExport(); assert.equal(state.snapshot().error, null);
});

test('malformed schemas, values and document names are rejected', () => {
  assert.throws(() => new FormSession([{ label: 'Missing ID' }]));
  assert.throws(() => new FormSession([{ id: 'x', label: 'X' }, { id: 'x', label: 'Again' }]));
  const state = make();
  const token = state.beginLoad('a');
  assert.throws(() => state.finishLoad(token, { secret_external_field: 'Unknown' }));
  assert.throws(() => state.finishLoad(token, { demo_name: false }));
  state.finishLoad(token, { demo_name: 'Synthetic' });
  const pending = exportStart(state);
  assert.throws(() => state.finishExport(pending.token, { ...artifact(), filename: '../private.txt' }));
  assert.equal(state.document(), null);
});
