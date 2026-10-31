import test from 'node:test';
import assert from 'node:assert/strict';
import { readRequirements } from './dossier-model';

test('source rows preserve wording, quantities, conditions and ordering without classifying document kinds', () => {
  const text = 'Một bản A hoặc B, nếu đáp ứng điều kiện; chưa rõ trường hợp C.\nGiữ nguyên dòng.';
  const rows = readRequirements([{ id: 2, position: 1, group_heading: 'Hướng dẫn', text_verbatim: 'Một bộ hồ sơ', originals: null, copies: null, form_ids: [] }, { id: 1, position: 0, group_heading: 'Điều kiện', text_verbatim: text, originals: 1, copies: 0, form_ids: [10, 20] }], [10, 20])!;
  assert.equal(rows[0].text, text); assert.deepEqual(rows[0].formIds, [10, 20]);
  assert.equal(rows[0].copies, 0); assert.equal(rows[1].originals, null);
  assert.equal(Object.hasOwn(rows[0], 'required'), false);
});
test('unknown requirements remain unknown; foreign form associations and invalid counts are rejected', () => {
  assert.equal(readRequirements(undefined, []), undefined);
  const row = { id: 1, position: 0, group_heading: '', text_verbatim: 'Source instruction', originals: 1, copies: 0, form_ids: [12] };
  assert.throws(() => readRequirements([row], [10]));
  assert.throws(() => readRequirements([{ ...row, originals: -1 }], [12]));
});
