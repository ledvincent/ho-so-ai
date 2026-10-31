import test from 'node:test';
import assert from 'node:assert/strict';
import { activeFields, canDownload, captureReview, emptyValues, example, issues, payloadValues, schema, updateValue } from './model';
import { assistantRequest, mockTransport, requests } from './transport';

test('published NA5 schema keeps draft status, all 43 definitions and fixed stay extension', () => {
  assert.equal(schema.fields.length, 43); assert.equal(schema.procedure_code, '1.001146'); assert.equal(schema.review_status, 'draft');
  assert.deepEqual(emptyValues(), { request_type: 'stay_extension' });
  assert.throws(() => updateValue(emptyValues(), 'request_type', 'visa_issuance'));
  assert.throws(() => updateValue(emptyValues(), 'personal_id', '000000000001'));
});
test('sponsor changes remove inactive data without mapping applicant fields to sponsor fields', () => {
  const organisation = { ...example, ...emptyValues() };
  const family = updateValue(organisation, 'host_type', 'family');
  assert.equal(family.organisation_name, undefined); assert.equal(family.applicant_full_name, example.applicant_full_name);
  assert.equal(activeFields(family).some(field => field.id === 'sponsor_full_name'), true);
  assert.equal(activeFields(family).some(field => field.id === 'sponsor_card_number'), false);
  assert.equal(activeFields(updateValue(family, 'sponsor_kind', 'foreign_resident')).some(field => field.id === 'sponsor_card_number'), true);
  assert.equal(payloadValues(family).applicant_signature, undefined);
});
test('producer example validates; impossible dates and chronology fail; nationality fields stay distinct', () => {
  assert.deepEqual(issues(example), {});
  assert.ok(issues({ ...example, birth_date: '1990-02-31' }).birth_date);
  assert.ok(issues({ ...example, extension_until: '2040-01-01' }).passport_expiry);
  const edited = updateValue(example, 'current_nationality', 'Example nation');
  assert.equal(edited.birth_nationality, 'France');
  assert.equal(payloadValues(example).applicant_full_name, 'ÉLODIE EXEMPLE');
});
test('review is immutable and draft or stale review cannot unlock a download', () => {
  const review = captureReview(example, 1);
  assert.ok(Object.isFrozen(review.values));
  assert.equal(canDownload('draft', review, 1, 'not-a-real-token', true), false);
  assert.equal(canDownload('reviewed', review, 2, 'token', true), false);
  assert.equal(canDownload('reviewed', review, 1, null, true), false);
});
test('wire requests match producer; assistant response has no field updates', async () => {
  assert.deepEqual(Object.keys(requests.preview(example).body), ['values']);
  assert.deepEqual(Object.keys(requests.download(example, 'token', true).body), ['values', 'review_token', 'confirmed']);
  const request = assistantRequest('Test request', Array.from({ length: 20 }, () => ({ role: 'user' as const, content: 'test' })));
  assert.equal(request.body.history.length, 12); assert.equal(request.body.procedure_code, '1.001146');
  const response = await mockTransport.chat(request);
  assert.deepEqual(Object.keys(response), ['status', 'answer', 'citations', 'model']);
  assert.equal(response.status, 'insufficient_context');
});
