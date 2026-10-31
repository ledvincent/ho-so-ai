import test from 'node:test';
import assert from 'node:assert/strict';
import recordedChat from '@/lib/discovery/fixtures/e162-chat-response.json';
import recordedDocuments from '@/lib/discovery/fixtures/e162-procedure-documents.json';
import recordedSchema from '@/lib/discovery/fixtures/e162-na5-schema.json';
import { createDiscoveryAdapter, readAnswer } from './api';
import { readDocumentCards, readFormAction, sameDocument } from './document-model';
import { readDocumentPages, readDocumentSchema } from './document-schema';
import { supportsNa5Profile } from './document-compat';
import { emptyValues, payloadValues, updateValue, issues } from '@/components/na5-demo/model';
import { nextMissing } from '@/components/guided-portal/state';
import { SessionExpired, type LocalSession } from '@/components/guided-portal/api';

// Checked-in public producer contracts and fictional transport; no live/model calls.
const action = readFormAction(recordedDocuments.documents[0]);
const documentSchema = readDocumentSchema(recordedSchema, action);
const workflow = { action, schema: documentSchema, pages: [] };
const session: LocalSession = { user: { id: 'fictional-owner', username: 'fixture', identity_provider: 'local' }, expires_at: 1900000000 };
const signal = () => new AbortController().signal;
const png = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a1ZkAAAAASUVORK5CYII=';
function smallSchema() {
  return readDocumentSchema({ ...recordedSchema, document_id: 'different-form', form_id: 'SMALL', page_count: 1,
    fields: [{ id: 'branch', label: 'Branch', type: 'choice', options: ['yes', 'no'] }, { id: 'Detail:1', label: 'Detail', type: 'text', required: true, when: { branch: 'yes' }, uppercase: true }, { id: 'signature', label: 'Sign manually', type: 'text', required: true, manual: true }], fixed_values: {}, date_order: []
  }, { ...action, document_id: 'different-form', form_id: 'SMALL' });
}

test('public partial answer retains distinct supporting, conditional and submission cards', () => {
  const result = readAnswer(recordedChat);
  assert.equal(result.status, 'insufficient_context');
  assert.equal(result.procedureCode, action.procedure_code);
  assert.ok(result.documents?.some(card => card.kind === 'submission_instruction' && card.form === null));
  assert.ok(result.documents?.some(card => card.requirement === 'conditional' && card.condition));
  assert.equal(result.documents?.find(card => card.form)?.form?.schema_url, action.schema_url);
  assert.throws(() => readDocumentCards(recordedChat.documents, []));
});

test('signed clarification is preserved exactly and choices cannot exist without matching state', async () => {
  const state = 'opaque.signed.state'; const body: unknown[] = [];
  const response = { status: 'needs_clarification', answer: 'Choose scope', model: null, citations: [], choices: [{ id: 'returned-choice', label: 'Provincial office' }], retrieval_state: state, procedure_code: null, documents: [] };
  assert.equal(readAnswer(response).retrievalState, state);
  assert.throws(() => readAnswer({ ...response, retrieval_state: null }));
  const client = createDiscoveryAdapter(session, (async (path, init) => {
    if (path === '/api/auth/session') return Response.json(session);
    body.push(JSON.parse(String(init?.body))); return Response.json(response);
  }) as typeof fetch);
  await client.chat('Fictional request', [], '1.001146', signal(), { retrievalState: state, clarificationAnswer: 'returned-choice' });
  assert.deepEqual(body[0], { message: 'Fictional request', history: [], retrieval_state: state, clarification_answer: 'returned-choice' });
});

test('a session change wins over a stale or unavailable document response', async () => {
  for (const status of [409, 503]) {
    let sessionCalls = 0;
    const client = createDiscoveryAdapter(session, (async path => {
      if (path === '/api/auth/session') { sessionCalls++; return Response.json(sessionCalls === 1 ? session : { ...session, user: { ...session.user, id: 'other-fictional-owner' } }); }
      return Response.json({ error: 'safe' }, { status });
    }) as typeof fetch);
    await assert.rejects(client.documents!('1.001146', signal()), SessionExpired);
  }
});

test('the narrow profile and legacy assistant bridge checks full schema and edition identity', () => {
  assert.equal(supportsNa5Profile(workflow), true);
  for (const key of ['document_id', 'form_id', 'procedure_code', 'template_sha256', 'template_version', 'revision'] as const) {
    assert.equal(supportsNa5Profile({ ...workflow, action: { ...action, [key]: 'changed' } }), false);
  }
  assert.equal(supportsNa5Profile({ ...workflow, schema: { ...documentSchema, fields: documentSchema.fields.map((field, index) => index ? field : { ...field, max_length: field.max_length + 1 }) } }), false);
  assert.equal(sameDocument(action, { ...action, template_version: 'b'.repeat(64) }), false);
});

test('a different small document uses its own optional, conditional, manual and uppercase fields', () => {
  const schema = smallSchema(); let values = emptyValues(schema);
  assert.equal(nextMissing(values, schema), null);
  values = updateValue(values, 'branch', 'yes', schema);
  assert.equal(nextMissing(values, schema)?.id, 'Detail:1');
  values = updateValue(values, 'Detail:1', 'fictional', schema);
  assert.equal(values['Detail:1'], 'FICTIONAL');
  assert.throws(() => updateValue(values, 'signature', 'forged', schema));
  assert.throws(() => updateValue(values, 'passport_number', 'borrowed', schema));
  values = updateValue(values, 'branch', 'no', schema);
  assert.equal(Object.hasOwn(values, 'Detail:1'), false);
  assert.deepEqual(payloadValues(values, schema), { branch: 'no' });
  assert.deepEqual(issues(values, schema), {});
  assert.equal(supportsNa5Profile({ action, schema, pages: [] }), false);
});

test('pages are document-sized and reject another edition, non-PNG or duplicate numbering', () => {
  const schema = smallSchema(); const page = { page_number: 1, image_data_url: png };
  assert.equal(readDocumentPages({ template_version: schema.template_version, pages: [page] }, schema).length, 1);
  assert.throws(() => readDocumentPages({ template_version: 'b'.repeat(64), pages: [page] }, schema));
  assert.throws(() => readDocumentPages({ template_version: schema.template_version, pages: [{ ...page, image_data_url: 'https://example.test/image.png' }] }, schema));
  assert.throws(() => readDocumentPages({ template_version: documentSchema.template_version, pages: [page, page, page] }, documentSchema));
});

test('validation uses whole normalized snapshot and exact template; changed service values are rejected', async () => {
  const schema = smallSchema(); const form = { ...workflow, schema }; const sent: any[] = [];
  let changed = false;
  const client = createDiscoveryAdapter(session, (async (path, init) => {
    if (path === '/api/auth/session') return Response.json(session);
    const body = JSON.parse(String(init?.body)); sent.push(body);
    return Response.json({ values: changed ? { branch: 'yes', 'Detail:1': 'CHANGED' } : body.values, template_version: schema.template_version, missing_fields: [], ready_for_preview: true, note: 'Fictional check' });
  }) as typeof fetch);
  const result = await client.validateDocument!(form, { branch: 'yes', 'Detail:1': 'fictional' }, signal());
  assert.equal(result.ready, true);
  assert.deepEqual(sent[0], { values: { branch: 'yes', 'Detail:1': 'FICTIONAL' }, template_version: schema.template_version });
  changed = true;
  await assert.rejects(client.validateDocument!(form, { branch: 'yes', 'Detail:1': 'fictional' }, signal()));
});

test('preview returns only checked pages and requires the protected review header', async () => {
  const schema = smallSchema(); let hasHeader = true;
  const client = createDiscoveryAdapter(session, (async path => {
    if (path === '/api/auth/session') return Response.json(session);
    return Response.json({ template_version: schema.template_version, pages: [{ page_number: 1, image_data_url: png }] }, { headers: hasHeader ? { 'X-Review-Token': 'fictional-opaque-token' } : {} });
  }) as typeof fetch);
  assert.deepEqual(await client.previewDocument!({ ...workflow, schema }, { branch: 'no' }, signal()), [{ pageNumber: 1, imageUrl: png }]);
  hasHeader = false;
  await assert.rejects(client.previewDocument!({ ...workflow, schema }, { branch: 'no' }, signal()));
});
