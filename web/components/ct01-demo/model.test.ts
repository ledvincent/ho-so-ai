import test from 'node:test';
import assert from 'node:assert/strict';
import { captureCt01, ct01DateParts, ct01SnapshotIsCurrent, editCt01Draft, newCt01Draft, resolveCt01Answer, SAMPLE_CT01, validateCt01 } from './model';

test('a new CT01 draft is blank and reports all three checkpoint fields missing', () => {
  const draft = newCt01Draft();
  assert.deepEqual(Object.values(draft.values), ['', '', '']);
  assert.equal(Object.keys(validateCt01(draft.values)).length, 3);
});
test('ID remains a document-local string with leading zeroes', () => {
  assert.deepEqual(resolveCt01Answer('personal_id', '000000000001'), { kind: 'apply', field: 'personal_id', value: '000000000001' });
  for (const input of ['1', '00000000000a', '000 000 000 001']) assert.equal(resolveCt01Answer('personal_id', input).kind, 'clarify');
});
test('ambiguous dates and impossible days are not inferred', () => {
  for (const input of ['12/10/1990', '1990-02-30', '90-10-12']) assert.equal(resolveCt01Answer('date_of_birth', input).kind, 'clarify');
  assert.equal(resolveCt01Answer('date_of_birth', '2000-02-29').kind, 'apply');
  assert.deepEqual(ct01DateParts('2000-02-29'), ['29', '02', '2000']);
});
test('unselected, multiline and procedural questions ask for clarification', () => {
  assert.equal(resolveCt01Answer(null, 'Nguyễn Văn Mẫu').kind, 'clarify');
  assert.equal(resolveCt01Answer('full_name', 'Tên Mẫu\nNgày sinh 1990-10-12').kind, 'clarify');
  assert.equal(resolveCt01Answer('full_name', 'Tôi cần nộp hồ sơ gì?').kind, 'clarify');
});
test('review captures exact immutable values; a later edit invalidates the printable revision', () => {
  const draft = { values: { ...SAMPLE_CT01 }, revision: 3 };
  const snapshot = captureCt01(draft);
  assert.equal(ct01SnapshotIsCurrent(draft, snapshot), true);
  assert.throws(() => { (snapshot.values as { personal_id: string }).personal_id = '999999999999'; });
  const changed = editCt01Draft(draft, 'full_name', 'Nguyễn Văn Mẫu Mới');
  assert.equal(ct01SnapshotIsCurrent(changed, snapshot), false);
  assert.equal(snapshot.values.personal_id, '000000000001');
});
