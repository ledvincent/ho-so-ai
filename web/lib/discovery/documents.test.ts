/** Offline e162 wire tests. Public contract captures plus explicitly synthetic PDFs/values. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import recordedChat from './fixtures/e162-chat-response.json';
import recordedActions from './fixtures/e162-procedure-documents.json';
import recordedSchema from './fixtures/e162-na5-schema.json';
import { createDiscoveryClient, DiscoveryError, type DiscoveryChatRequest, type DiscoveryDocumentDownload, type JsonObject } from './upstream';

const C = recordedSchema.procedure_code;
const D = recordedSchema.document_id;
const V = recordedSchema.template_version;
const clone = <T>(value: T): T => structuredClone(value);
const TOKEN = 'SYNTHETIC_OPAQUE_VALUE.SYNTHETIC_SIGNATURE';
const PDF = new TextEncoder().encode('%PDF-1.7\nSYNTHETIC TRANSPORT FIXTURE, NOT AN OFFICIAL PDF\n%%EOF');
const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jipkAAAAASUVORK5CYII=';
const schemaPath = `/documents/${D}/schema`;
const formBody = () => ({ values: { applicant_full_name: 'SYNTHETIC APPLICANT', request_type: 'stay_extension' }, template_version: V });
const pageBody = () => ({ template_version: V, pages: Array.from({ length: recordedSchema.page_count }, (_, index) => ({ page_number: index + 1, image_data_url: PNG })) });
const json = (value: unknown, status = 200, headers: HeadersInit = {}) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', ...headers } });
type Call = { url: string; init: RequestInit };
type Reply = unknown | ((call: Call) => Response | Promise<Response>);
function fixture(routes: Record<string, Reply>, baseUrl = 'http://127.0.0.1:8123') {
  const calls: Call[] = [];
  const client = createDiscoveryClient({ baseUrl, workflow: {}, fetch: (async (url: string | URL | Request, init: RequestInit = {}) => {
    const call = { url: String(url), init }; calls.push(call);
    const path = new URL(call.url).pathname;
    if (!(path in routes)) throw new Error(`Unexpected synthetic fixture endpoint ${path}`);
    const reply = routes[path];
    return typeof reply === 'function' ? reply(call) : json(reply);
  }) as typeof fetch });
  return { client, calls };
}
function error(status: number, code: string) {
  return (value: unknown) => {
    assert.ok(value instanceof DiscoveryError);
    assert.equal(value.status, status); assert.equal(value.code, code); assert.equal(value.message, code);
    assert.equal(value.message.includes('SYNTHETIC_PRIVATE'), false);
    return true;
  };
}
function assertPrivateTransport(calls: Call[]) {
  for (const { init } of calls) {
    const headers = new Headers(init.headers);
    for (const key of ['authorization', 'cookie', 'origin', 'referer', 'x-review-token']) assert.equal(headers.has(key), false);
    assert.equal(init.credentials, 'omit'); assert.equal(init.redirect, 'error'); assert.equal(init.cache, 'no-store');
    assert.ok(init.signal instanceof AbortSignal);
  }
}

test('public e162 chat capture retains document citations which are not all printed inline', async () => {
  const { client, calls } = fixture({ '/assistant/chat': recordedChat });
  const result = await client.chat({ message: 'Please explain the paperwork.', procedure_code: C, history: [] });
  assert.equal(result.answer, recordedChat.answer);
  assert.deepEqual(result.citations, recordedChat.citations);
  assert.equal((result.documents as JsonObject[]).length, recordedChat.documents.length);
  const card = (result.documents as JsonObject[]).find(item => item.form !== null)!;
  const action = card.form as JsonObject;
  assert.equal(action.schema_url, `/api/discovery/documents/${D}/schema`);
  assert.equal(action.document_id, D);
  assert.equal(action.template_version, V);
  assertPrivateTransport(calls);
});

test('partial answers retain their independently sourced document cards', async () => {
  const capture = { ...clone(recordedChat), status: 'insufficient_context', answer: 'SYNTHETIC partial answer.' };
  const result = await fixture({ '/assistant/chat': capture }).client.chat({ message: 'Please explain the paperwork.' });
  assert.equal(result.status, 'insufficient_context');
  assert.deepEqual(result.citations, capture.citations);
  assert.equal((result.documents as unknown[]).length, capture.documents.length);
});

test('signed clarification state and choice IDs round-trip byte-for-byte without procedure inference', async () => {
  const state = 'SYNTHETIC_OPAQUE_STATE_WITH_PADDING==.signature';
  const choices = { status: 'needs_clarification', answer: 'Which procedure do you need?', citations: [], model: null,
    choices: [{ id: '0', label: 'SYNTHETIC first choice' }, { id: 'unknown', label: 'SYNTHETIC unsure' }],
    retrieval_state: state, procedure_code: null, documents: [] };
  const { client, calls } = fixture({ '/assistant/chat': choices });
  const result = await client.chat({ message: 'I need help with paperwork.', retrieval_state: null, clarification_answer: null });
  assert.equal(result.retrieval_state, state);
  await client.chat({ message: 'SYNTHETIC first choice', history: [], retrieval_state: state, clarification_answer: '0' });
  const body = JSON.parse(calls[1].init.body as string);
  assert.equal(body.retrieval_state, state); assert.equal(body.clarification_answer, '0');
  assert.equal('procedure_code' in body, false);
  assert.equal(new URL(calls[1].url).search, '');
  assertPrivateTransport(calls);
});

test('unsigned choices, stale-state input shapes and unrecognized chat fields fail before fetch', async () => {
  const { client, calls } = fixture({});
  for (const input of [
    { message: 'SYNTHETIC', clarification_answer: '0' },
    { message: 'SYNTHETIC', retrieval_state: 'state', clarification_answer: '0', procedure_code: C },
    { message: 'SYNTHETIC', retrieval_state: 'x'.repeat(12001) },
    { message: 'SYNTHETIC', retrieval_state: 'SYNTHETIC_PRIVATE\nSTATE' },
    { message: 'SYNTHETIC', history: null },
    { message: 'SYNTHETIC', values: { applicant_full_name: 'SYNTHETIC_PRIVATE_NAME' } },
  ]) await assert.rejects(client.chat(input as DiscoveryChatRequest), error(422, 'INVALID_REQUEST'));
  assert.equal(calls.length, 0);
});

test('unresolvable markers, unsigned response choices and unrelated document sources are rejected', async () => {
  const candidates: JsonObject[] = [
    { ...clone(recordedChat), answer: 'SYNTHETIC answer [unknown-source]' },
    { ...clone(recordedChat), choices: [{ id: '0', label: 'SYNTHETIC' }], retrieval_state: null },
  ];
  const sourceMismatch = clone(recordedChat) as JsonObject;
  (sourceMismatch.documents as JsonObject[])[0].source_ids = ['unknown-source'];
  candidates.push(sourceMismatch);
  for (const response of candidates) await assert.rejects(fixture({ '/assistant/chat': response }).client.chat({ message: 'SYNTHETIC question' }), error(502, 'DISCOVERY_INVALID_RESPONSE'));
});

test('setup is one non-generating fixed-path read and projects no upstream secrets', async () => {
  const expected = { generation_configured: true, index_ready: true, procedures: [{ code: C, name: 'SYNTHETIC procedure', name_en: 'SYNTHETIC procedure EN' }], model: 'synthetic-model', reasoning_effort: 'medium' };
  const { client, calls } = fixture({ '/assistant/setup': { ...expected, api_key: 'SYNTHETIC_PRIVATE_KEY' } });
  assert.deepEqual(await client.setup(), expected);
  assert.equal(calls.length, 1); assert.equal(calls[0].init.method, 'GET');
  assertPrivateTransport(calls);
});

test('setup preserves configured/index readiness independently and rejects malformed catalogs', async () => {
  const configured = { generation_configured: false, index_ready: true, procedures: [], model: '', reasoning_effort: null };
  assert.deepEqual(await fixture({ '/assistant/setup': configured }).client.setup(), configured);
  for (const bad of [{ ...configured, index_ready: 'true' }, { ...configured, procedures: [{ code: '../bad', name: 'SYNTHETIC', name_en: 'SYNTHETIC' }] }]) {
    await assert.rejects(fixture({ '/assistant/setup': bad }).client.setup(), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  }
});

test('new search wire keeps release/degraded/matched_by and never fabricates similarity', async () => {
  const expected = { status: 'found', release_id: 'synthetic-release', degraded: true,
    results: [{ code: C, name: 'SYNTHETIC candidate', score: 0.032, matched_by: ['keyword', 'typo'] }] };
  const result = await fixture({ '/search': { ...expected, secret: 'SYNTHETIC_PRIVATE' } }).client.search('SYNTHETIC request');
  assert.deepEqual(result, expected);
  assert.equal('similarity' in (result.results as JsonObject[])[0], false);
  const unavailable = { status: 'unavailable', release_id: 'synthetic-release', degraded: true, results: [] };
  assert.deepEqual(await fixture({ '/search': unavailable }).client.search('SYNTHETIC request'), unavailable);
  await assert.rejects(fixture({ '/search': { ...unavailable, degraded: false } }).client.search('SYNTHETIC request'), error(502, 'DISCOVERY_INVALID_RESPONSE'));
});

test('installed public document actions preserve metadata and rewrite every server-owned path', async () => {
  const { client, calls } = fixture({ [`/procedures/${C}/documents`]: recordedActions });
  const result = await client.documents(C);
  const action = (result.documents as JsonObject[])[0];
  for (const key of ['template_version', 'template_sha256', 'revision', 'applicability', 'review_status', 'download_available']) assert.deepEqual(action[key], recordedActions.documents[0][key as keyof typeof recordedActions.documents[0]]);
  for (const [key, value] of Object.entries(recordedActions.documents[0])) if (key.endsWith('_url')) assert.equal(action[key], '/api/discovery' + value);
  assertPrivateTransport(calls);
});

test('malicious action URLs, procedure mismatches and counterfeit approval metadata fail closed', async () => {
  const actions = recordedActions.documents[0];
  for (const changes of [
    { schema_url: 'https://attacker.invalid/steal' }, { preview_url: '//attacker.invalid/steal' },
    { download_url: '/documents/other-document/download' }, { procedure_code: '1.003342' },
    { document_id: '../private' }, { download_available: true, review_status: 'draft' },
  ]) {
    const { client, calls } = fixture({ [`/procedures/${C}/documents`]: { documents: [{ ...actions, ...changes }] } });
    await assert.rejects(client.documents(C), error(502, 'DISCOVERY_INVALID_RESPONSE'));
    assert.equal(calls.length, 1);
  }
});

test('generic schema accepts the complete public e162 schema with uppercase/placement/date metadata', async () => {
  const { client } = fixture({ [schemaPath]: recordedSchema });
  const result = await client.documentSchema(D);
  assert.deepEqual(result, recordedSchema);
  assert.equal(result.fields[0].uppercase, true);
  assert.deepEqual(result.date_order, recordedSchema.date_order);
  assert.equal(result.review_status, 'draft'); assert.equal(result.download_available, false);
});

test('a second generic document uses its own ID, procedure, fields and page count without NA5 assumptions', async () => {
  const id = 'a_' + 'x'.repeat(98);
  const expected = { ...clone(recordedSchema), document_id: id, procedure_code: '2.000123', form_id: 'SYNTHETIC-FORM', page_count: 1,
    fields: [{ id: 'Person.Name', label: 'SYNTHETIC name', type: 'text', required: false }, { id: 'DATE:Birth', label: 'SYNTHETIC date', type: 'date' }],
    fixed_values: {}, date_order: [] };
  const { client, calls } = fixture({ [`/documents/${id}/schema`]: expected });
  assert.deepEqual(await client.documentSchema(id), expected);
  assert.equal(calls[0].url.endsWith(`/documents/${id}/schema`), true);
});

test('document IDs never become arbitrary paths or URLs', async () => {
  const { client, calls } = fixture({});
  for (const id of ['../private', `${D}?x=1`, 'https://evil.invalid', `${D}/download`, 'a'.repeat(101), 'UPPERCASE']) {
    await assert.rejects(client.documentSchema(id), error(422, 'INVALID_REQUEST'));
  }
  assert.equal(calls.length, 0);
});

test('wrong schema identity, malformed branch references and duplicate fields cannot enable an editor', async () => {
  const malformed: JsonObject[] = [
    { ...clone(recordedSchema), document_id: 'another-document' },
    { ...clone(recordedSchema), download_available: true },
    { ...clone(recordedSchema), page_count: 0 },
    { ...clone(recordedSchema), fields: [recordedSchema.fields[0], recordedSchema.fields[0]] },
    { ...clone(recordedSchema), fixed_values: { missing_field: 'SYNTHETIC' } },
    { ...clone(recordedSchema), date_order: [['birth_date', 'unknown_field']] },
  ];
  const badBranch = clone(recordedSchema) as JsonObject;
  (badBranch.fields as JsonObject[])[0].when = { unknown_field: 'SYNTHETIC' };
  malformed.push(badBranch);
  for (const schema of malformed) await assert.rejects(fixture({ [schemaPath]: schema }).client.documentSchema(D), error(502, 'DISCOVERY_INVALID_RESPONSE'));
});

test('blank template checks PDF MIME/signature and never mistakes original DOCX hash for converted PDF hash', async () => {
  const { client, calls } = fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/template`]: () => new Response(PDF, { headers: { 'Content-Type': 'application/pdf' } }) });
  const result = await client.documentTemplate(D);
  assert.deepEqual(result.bytes, PDF); assert.equal(result.contentType, 'application/pdf'); assert.equal(result.filename, `${D}-template.pdf`);
  assert.notEqual(createHash('sha256').update(PDF).digest('hex'), recordedSchema.template_sha256);
  assert.equal(calls.length, 2); assertPrivateTransport(calls);
});

test('wrong binary MIME, HTML and empty payloads are not returned as document PDFs', async () => {
  for (const reply of [
    () => new Response(PDF, { headers: { 'Content-Type': 'text/html' } }),
    () => new Response('<html>SYNTHETIC_PRIVATE</html>', { headers: { 'Content-Type': 'application/pdf' } }),
    () => new Response('', { headers: { 'Content-Type': 'application/pdf' } }),
  ]) await assert.rejects(fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/template`]: reply }).client.documentTemplate(D), error(502, 'DISCOVERY_INVALID_RESPONSE'));
});

test('template pages preserve exact version/count and accept only numbered PNG data URLs', async () => {
  const expected = pageBody();
  assert.deepEqual(await fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/template-pages`]: expected }).client.documentPages(D), expected);
  for (const changes of [
    { template_version: 'f'.repeat(64) }, { pages: expected.pages.slice(1) },
    { pages: expected.pages.map((page, index) => index ? page : { ...page, page_number: 0 }) },
    { pages: expected.pages.map(page => ({ ...page, image_data_url: 'https://attacker.invalid/image' })) },
    { pages: expected.pages.map(page => ({ ...page, image_data_url: 'data:image/svg+xml;base64,PHN2Zz4=' })) },
    { pages: expected.pages.map(page => ({ ...page, image_data_url: 'data:image/png;base64,not-png' })) },
  ]) await assert.rejects(fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/template-pages`]: { ...expected, ...changes } }).client.documentPages(D), error('template_version' in changes ? 409 : 502, 'template_version' in changes ? 'WORKFLOW_VERSION_MISMATCH' : 'DISCOVERY_INVALID_RESPONSE'));
});

test('partial validate forwards the whole explicit values snapshot and preserves normalized result/missing fields', async () => {
  const body = formBody(), before = clone(body);
  const expected = { values: { applicant_full_name: 'SYNTHETIC APPLICANT', request_type: 'stay_extension' }, missing_fields: [{ id: 'sex', label: 'Sex' }], ready_for_preview: false, template_version: V, note: 'SYNTHETIC validation result' };
  const { client, calls } = fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/validate`]: expected });
  assert.deepEqual(await client.documentValidate(D, body), expected);
  assert.deepEqual(JSON.parse(calls[1].init.body as string), body); assert.deepEqual(body, before);
  assertPrivateTransport(calls);
});

test('stale versions and unknown/non-string values stop before any document mutation', async () => {
  for (const body of [
    { ...formBody(), template_version: 'f'.repeat(64) }, { ...formBody(), values: { unknown_field: 'SYNTHETIC_PRIVATE' } },
    { ...formBody(), values: { applicant_full_name: null } }, { ...formBody(), values: [] },
    { ...formBody(), profile_id: 'SYNTHETIC_PRIVATE_PROFILE' }, { values: {} },
  ]) {
    const { client, calls } = fixture({ [schemaPath]: recordedSchema });
    await assert.rejects(client.documentValidate(D, body as ReturnType<typeof formBody>), error('template_version' in body && body.template_version === 'f'.repeat(64) ? 409 : 422, 'template_version' in body && body.template_version === 'f'.repeat(64) ? 'WORKFLOW_VERSION_MISMATCH' : 'INVALID_REQUEST'));
    assert.equal(calls.length, 1); assert.equal(calls[0].init.method, 'GET');
  }
});

test('validate rejects forged normalized fields and impossible ready/missing combinations', async () => {
  const expected = { values: {}, missing_fields: [], ready_for_preview: true, template_version: V, note: 'SYNTHETIC validation' };
  for (const changes of [
    { values: { unknown_field: 'SYNTHETIC_PRIVATE' } },
    { missing_fields: [{ id: 'unknown_field', label: 'SYNTHETIC' }], ready_for_preview: false },
    { missing_fields: [{ id: 'sex', label: 'Wrong label' }], ready_for_preview: false },
    { ready_for_preview: false }, { template_version: 'f'.repeat(64) },
  ]) await assert.rejects(fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/validate`]: { ...expected, ...changes } }).client.documentValidate(D, formBody()), error('template_version' in changes ? 409 : 502, 'template_version' in changes ? 'WORKFLOW_VERSION_MISMATCH' : 'DISCOVERY_INVALID_RESPONSE'));
});

test('PDF preview exposes only bytes/MIME and the exact opaque review header to its authenticated root', async () => {
  const { client, calls } = fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/preview`]: () => new Response(PDF, { headers: { 'Content-Type': 'application/pdf', 'X-Review-Token': TOKEN, 'X-Upstream-Secret': 'SYNTHETIC_PRIVATE' } }) });
  const result = await client.documentPreview(D, formBody(), false);
  assert.deepEqual(result, { bytes: PDF, contentType: 'application/pdf', reviewToken: TOKEN });
  assert.equal(JSON.stringify(result).includes('SYNTHETIC_PRIVATE'), false);
  assert.equal(new URL(calls[1].url).search, ''); assertPrivateTransport(calls);
});

test('page preview keeps producer JSON unchanged and preserves its separate review header', async () => {
  const expected = pageBody();
  const { client, calls } = fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/preview-pages`]: () => json(expected, 200, { 'X-Review-Token': TOKEN }) });
  assert.deepEqual(await client.documentPreview(D, formBody(), true), { data: expected, contentType: 'application/json', reviewToken: TOKEN });
  assert.deepEqual(JSON.parse(calls[1].init.body as string), formBody()); assertPrivateTransport(calls);
});

test('preview never succeeds without a review token or with oversized token metadata', async () => {
  for (const token of [null, '', 'x'.repeat(131073)]) {
    const { client } = fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/preview`]: () => new Response(PDF, { headers: { 'Content-Type': 'application/pdf', ...(token === null ? {} : { 'X-Review-Token': token }) } }) });
    await assert.rejects(client.documentPreview(D, formBody(), false), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  }
});

test('draft final-download gate stops before a producer download request even with confirmation/token', async () => {
  const { client, calls } = fixture({ [schemaPath]: recordedSchema });
  await assert.rejects(client.documentDownload(D, { ...formBody(), review_token: TOKEN, confirmed: true }), error(409, 'DISCOVERY_NOT_READY'));
  assert.equal(calls.length, 1);
});

test('reviewed downloads require explicit confirmation and forward exact values/version/token only', async () => {
  const schema = { ...clone(recordedSchema), review_status: 'reviewed', download_available: true };
  const { client, calls } = fixture({ [schemaPath]: schema, [`/documents/${D}/download`]: () => new Response(PDF, { headers: { 'Content-Type': 'application/pdf' } }) });
  const body: DiscoveryDocumentDownload = { ...formBody(), review_token: TOKEN, confirmed: true };
  const result = await client.documentDownload(D, body);
  assert.deepEqual(result, { bytes: PDF, contentType: 'application/pdf', filename: `${D}-filled.pdf` });
  assert.deepEqual(JSON.parse(calls[1].init.body as string), body); assertPrivateTransport(calls);
  for (const bad of [{ ...body, confirmed: false }, { ...body, review_token: '' }, { ...body, confirmed: 1 }]) {
    const failed = fixture({ [schemaPath]: schema });
    await assert.rejects(failed.client.documentDownload(D, bad as DiscoveryDocumentDownload), error(422, 'INVALID_REQUEST'));
    assert.equal(failed.calls.length, 1);
  }
});

test('producer validation/stale/provider errors retain statuses without raw PII or secret text', async () => {
  for (const [status, expected, code] of [[422, 422, 'INVALID_REQUEST'], [409, 409, 'DISCOVERY_NOT_READY'], [502, 502, 'DISCOVERY_INVALID_RESPONSE'], [503, 503, 'DISCOVERY_UNAVAILABLE'], [504, 504, 'DISCOVERY_TIMEOUT']] as const) {
    const { client, calls } = fixture({ [schemaPath]: recordedSchema, [`/documents/${D}/validate`]: () => json({ detail: 'SYNTHETIC_PRIVATE_VALUE_AND_INTERNAL_PATH' }, status) });
    await assert.rejects(client.documentValidate(D, formBody()), error(expected, code)); assert.equal(calls.length, 2);
  }
});

test('schema and PDF redirect responses cannot redirect the private caller or trigger another fetch', async () => {
  for (const endpoint of ['schema', 'template']) {
    const { client, calls } = fixture({ [schemaPath]: endpoint === 'schema' ? () => Response.redirect('https://attacker.invalid', 302) : recordedSchema,
      [`/documents/${D}/template`]: () => Response.redirect('https://attacker.invalid', 307) });
    await assert.rejects(client.documentTemplate(D), error(502, 'DISCOVERY_INVALID_RESPONSE'));
    assert.equal(calls.length, endpoint === 'schema' ? 1 : 2);
  }
});

test('a full allowed Unicode chat history stays below the independent one-MiB request cap', async () => {
  const response = { status: 'insufficient_context', answer: 'SYNTHETIC answer', citations: [], model: null, choices: [], retrieval_state: null, procedure_code: null, documents: [] };
  const { client, calls } = fixture({ '/assistant/chat': response });
  await client.chat({ message: '😀'.repeat(1000), history: Array.from({ length: 12 }, () => ({ role: 'user', content: '😀'.repeat(16000) })) });
  assert.ok(Buffer.byteLength(calls[0].init.body as string) > 400 * 1024);
  assert.ok(Buffer.byteLength(calls[0].init.body as string) < 1024 * 1024);
});

test('document request byte limits prevent oversized values from being posted', async () => {
  const values = Object.fromEntries(recordedSchema.fields.map(field => [field.id, '😀'.repeat(16000)]));
  const { client, calls } = fixture({ [schemaPath]: recordedSchema });
  await assert.rejects(client.documentValidate(D, { values, template_version: V }), error(413, 'REQUEST_TOO_LARGE'));
  assert.equal(calls.length, 1);
});

test('regular document calls abort after twenty seconds including a blocked response stream', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  let aborted = false, cancelled = false;
  const client = createDiscoveryClient({ workflow: {}, baseUrl: 'http://127.0.0.1:8123', fetch: (async (_url, init) => {
    init?.signal?.addEventListener('abort', () => { aborted = true; });
    return new Response(new ReadableStream<Uint8Array>({ pull() {}, cancel() { cancelled = true; } }), { headers: { 'Content-Type': 'application/json' } });
  }) as typeof fetch });
  const pending = client.documentSchema(D);
  await Promise.resolve(); await Promise.resolve();
  t.mock.timers.tick(20000);
  await assert.rejects(pending, error(504, 'DISCOVERY_TIMEOUT'));
  assert.equal(aborted, true); assert.equal(cancelled, true);
});

test('chat deadline allows the producer 120-second model call and aborts at 180 seconds', async t => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  let aborted = false, settled = false;
  const client = createDiscoveryClient({ workflow: {}, baseUrl: 'http://127.0.0.1:8123', fetch: (async (_url, init) => {
    init?.signal?.addEventListener('abort', () => { aborted = true; });
    return new Promise<Response>(() => {});
  }) as typeof fetch });
  const pending = client.chat({ message: 'SYNTHETIC question' });
  void pending.catch(() => { settled = true; });
  t.mock.timers.tick(179999); await Promise.resolve();
  assert.equal(aborted, false); assert.equal(settled, false);
  t.mock.timers.tick(1);
  await assert.rejects(pending, error(504, 'DISCOVERY_TIMEOUT'));
  assert.equal(aborted, true);
});

test('base origin rejects normalized dot-path configuration rather than silently discarding a base path', async () => {
  for (const base of ['https://producer.invalid/other/..', 'http://127.attacker.invalid']) {
    const { client, calls } = fixture({}, base);
    await assert.rejects(client.setup(), error(503, 'DISCOVERY_UNAVAILABLE'));
    assert.equal(calls.length, 0);
  }
});

test('large page data URLs are processed linearly and preserve PNG-only boundaries', async () => {
  const bytes = Buffer.alloc(1024 * 1024); Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).copy(bytes);
  const data = 'data:image/png;base64,' + bytes.toString('base64');
  const schema = { ...clone(recordedSchema), page_count: 1 };
  const response = { template_version: V, pages: [{ page_number: 1, image_data_url: data }] };
  assert.deepEqual(await fixture({ [schemaPath]: schema, [`/documents/${D}/template-pages`]: response }).client.documentPages(D), response);
});
