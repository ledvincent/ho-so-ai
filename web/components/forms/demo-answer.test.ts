import test from 'node:test';
import assert from 'node:assert/strict';
import { EMPTY_PROFILE, PROFILE_LIMITS } from '@/lib/contracts';
import { nextChatField, resolveDemoAnswer } from './demo-answer';

test('an explicit known field is required; unknown keys never become targets', () => {
  for (const target of [null, undefined, '', 'owner', '__proto__']) {
    assert.equal(resolveDemoAnswer(target, 'Nguyễn Văn Mẫu').kind, 'clarify');
  }
});

test('one literal answer returns only the selected field and preserves exact text', () => {
  const value = '  Nguyễn Văn Mẫu  ';
  assert.deepEqual(resolveDemoAnswer('full_name', value), { kind: 'apply', field: 'full_name', value });
  assert.deepEqual(resolveDemoAnswer('address', '123 đường Mẫu'), { kind: 'apply', field: 'address', value: '123 đường Mẫu' });
});

test('ambiguous and impossible dates clarify; valid ISO date is kept verbatim', () => {
  for (const answer of ['12/10/1990', '10-12-1990', '1990-2-01', '2026-02-30']) {
    assert.equal(resolveDemoAnswer('date_of_birth', answer).kind, 'clarify');
  }
  const ambiguous = resolveDemoAnswer('date_of_birth', '12/10/1990');
  assert.ok(ambiguous.kind === 'clarify' && ambiguous.message.includes('YYYY-MM-DD'));
  assert.deepEqual(resolveDemoAnswer('date_of_birth', '2000-02-29'), { kind: 'apply', field: 'date_of_birth', value: '2000-02-29' });
});

test('shared email validation and generated field bounds reject invalid answers', () => {
  for (const value of ['not-an-email', 'a@b', ' mau@example.test ']) assert.equal(resolveDemoAnswer('email', value).kind, 'clarify');
  assert.equal(resolveDemoAnswer('full_name', 'ắ'.repeat(PROFILE_LIMITS.full_name + 1)).kind, 'clarify');
  assert.equal(resolveDemoAnswer('address', 'x'.repeat(PROFILE_LIMITS.address + 1)).kind, 'clarify');
  assert.equal(resolveDemoAnswer('full_name', 'ắ'.repeat(PROFILE_LIMITS.full_name)).kind, 'apply');
});

test('multiple values, questions, legal requests and control characters clarify without applying', () => {
  for (const value of ['Tên: Nguyễn Văn Mẫu\nNgày sinh: 1990-10-12', 'Tôi cần nộp hồ sơ gì?', 'thủ tục cư trú', 'What documents are needed', 'name\tvalue', '   ']) {
    assert.equal(resolveDemoAnswer('full_name', value).kind, 'clarify');
  }
});

test('next-field guidance prefers missing values and does not mutate the canonical draft', () => {
  const values = { ...EMPTY_PROFILE, full_name: 'Mẫu', date_of_birth: '1990-10-12', nationality: 'Việt Nam' };
  const before = { ...values };
  assert.equal(nextChatField(values, 'full_name'), 'address');
  assert.deepEqual(values, before);
  const completed = { full_name: 'Mẫu', date_of_birth: '1990-10-12', nationality: 'Việt Nam', address: '123 đường Mẫu', phone_number: '+84 000', email: 'mau@example.test' };
  assert.equal(nextChatField(completed, 'email'), 'full_name');
});
