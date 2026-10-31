/** Synthetic consumer fixtures only. No producer imports, live retrieval or model calls. */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { createDiscoveryClient, DiscoveryError, type JsonObject, type DiscoveryChatRequest } from './upstream';

const C = '1.001146';
const H = 'a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751';
const SOURCE_HASH = 'b'.repeat(64);
const BASELINE = 'c'.repeat(64);
const OUTPUT = 'd'.repeat(64);
const clone = <T>(value: T): T => structuredClone(value);
function workflow(): JsonObject {
  return { procedure_code: C, form_sha256: H, revision_reference: 'SYNTHETIC revision', issued_on: '2026-01-01',
    effective_from: '2026-01-02', review_status: 'draft', pdf_path: `data/forms/_objects/${H}/blank.pdf`,
    mapping_metadata: { input_fingerprint: 'e'.repeat(64) }, fixed_values: { request_type: 'stay_extension' },
    fields: Array.from({ length: 43 }, (_, index) => ({ id: `synthetic_${index}`, label: `SYNTHETIC field ${index}`, type: 'text', required: false, when: {}, manual: false })),
  };
}
function envelope(sha = H): JsonObject {
  return { id: 7, run_id: 'synthetic-run-1', baseline_id: BASELINE, output_sha256: OUTPUT, metadata: {},
    profile: { procedure_code: { value: C, source_refs: [{ source_id: 'primary', locator: 'identity', quote: `SYNTHETIC procedure ${C}` }] },
      form_relationships: [{ file_hash: sha, field_schema_ref: `data/forms/_objects/${sha}/fields.json` }], decision_criteria: [] },
    sources: [{ source_id: 'primary', locator: 'identity', text: `SYNTHETIC procedure ${C}`, url: 'https://official.invalid/synthetic-source', sha256: SOURCE_HASH,
      kind: 'procedure', snapshot_id: 10, fetched_at: '2026-01-01T00:00:00Z' }],
  };
}
function snapshot(sha = H): JsonObject {
  const w = workflow();
  const provenance = { source_url: 'https://official.invalid/synthetic-source', sha256: SOURCE_HASH, fetched_at: '2026-01-01T00:00:00Z' };
  return { code: C, procedure_code: C, id: 10, ...provenance, name: 'SYNTHETIC procedure; not official data', status: 'parsed',
    analysis: { facts_ready: true, readiness: 'synthetic_ready' }, structured_profile: envelope(sha),
    forms: [{ id: 20, snapshot_id: 10, form_sha256: sha, source_url: 'https://official.invalid/synthetic-form', label: 'SYNTHETIC original',
      original_download_url: `/forms/${sha}/original`, linked_from: provenance, review_status: 'draft', revision_reference: w.revision_reference,
      issued_on: w.issued_on, effective_from: w.effective_from, pdf_path: w.pdf_path }],
    requirements: [{ id: 30, snapshot_id: 10, ...provenance, text_verbatim: 'SYNTHETIC requirement', form_ids: [20] }], facts: [], methods: [], fees: [],
  };
}
function analysis(): JsonObject {
  const w = workflow();
  return { sha256: H, review_status: w.review_status, revision_reference: w.revision_reference, issued_on: w.issued_on,
    effective_from: w.effective_from, pdf_path: w.pdf_path, mapping_metadata: w.mapping_metadata,
    fields_json: clone(w.fields), fields: [{ form_sha256: H, field_id: 'synthetic_0', page: 1 }], analysis_issues: [], source_metadata: {} };
}
function schema(): JsonObject {
  const w = workflow();
  return { procedure_code: C, name: 'SYNTHETIC workflow', revision: w.revision_reference, effective_from: w.effective_from,
    review_status: w.review_status, fields: clone(w.fields), fixed_values: clone(w.fixed_values) };
}
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
const chatFixture = (value: JsonObject) => ({ choices: [], retrieval_state: null, procedure_code: null, documents: [], ...value });
function error(status: number, code: string) {
  return (value: unknown) => { assert.ok(value instanceof DiscoveryError); assert.equal(value.status, status); assert.equal(value.code, code); assert.equal(value.message, code); return true; };
}
function fixture(routes: Record<string, unknown | (() => Response)>, baseUrl = 'http://127.0.0.1:8123') {
  const calls: { url: string; init: RequestInit }[] = [];
  const fetcher = (async (url: string | URL | Request, init: RequestInit = {}) => {
    calls.push({ url: String(url), init });
    const route = routes[new URL(String(url)).pathname];
    assert.notEqual(route, undefined, `Unexpected synthetic fixture route ${String(url)}`);
    if (typeof route === 'function') return route();
    const path = new URL(String(url)).pathname;
    if (path === '/search') return json({ release_id: 'synthetic-release', degraded: false, ...route as JsonObject });
    if (path === '/assistant/chat') return json(chatFixture(route as JsonObject));
    return json(route);
  }) as typeof fetch;
  return { calls, client: createDiscoveryClient({ baseUrl, fetch: fetcher, workflow: workflow() }) };
}

test('synthetic search preserves found, multiple and not_found without selecting a procedure', async () => {
  for (const results of [[], [{ code: C, name: 'SYNTHETIC A', score: 0.04, matched_by: ['keyword'] }],
    [{ code: C, name: 'SYNTHETIC A', score: 0.04, matched_by: ['keyword'] }, { code: '1.003342', name: 'SYNTHETIC B', score: 0.03, matched_by: ['semantic'] }]]) {
    const expected = { status: results.length ? 'found' : 'not_found', release_id: 'synthetic-release', degraded: false, results };
    const { client, calls } = fixture({ '/search': expected });
    assert.deepEqual(await client.search('  synthetic request  '), expected);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].init.body, JSON.stringify({ query: 'synthetic request' }));
  }
});
test('synthetic transport is fixed-origin, noncached, redirect-error, credential-free and abortable', async () => {
  const { client, calls } = fixture({ '/search': { status: 'not_found', results: [] } });
  await client.search('synthetic request');
  const call = calls[0];
  assert.equal(call.url, 'http://127.0.0.1:8123/search');
  assert.equal(call.init.redirect, 'error'); assert.equal(call.init.credentials, 'omit'); assert.equal(call.init.cache, 'no-store');
  assert.ok(call.init.signal instanceof AbortSignal);
  const headers = new Headers(call.init.headers);
  for (const name of ['authorization', 'cookie', 'origin', 'referer']) assert.equal(headers.has(name), false);
});
test('missing or unsafe origin fails lazily without upstream traffic', async () => {
  for (const baseUrl of [undefined, '', 'http://example.com', 'http://127.attacker.invalid', 'https://u:p@example.com', 'https://example.com/path', 'https://example.com/?x=1', 'https://example.com/#fragment', 'https://example.com\\@evil.invalid', ' https://example.com']) {
    let calls = 0;
    const client = createDiscoveryClient({ baseUrl, workflow: workflow(), fetch: (async () => { calls++; throw new Error(); }) as typeof fetch });
    await assert.rejects(client.search('synthetic request'), error(503, 'DISCOVERY_UNAVAILABLE'));
    assert.equal(calls, 0);
  }
});
test('HTTPS and explicit loopback HTTP origins are allowed', async () => {
  for (const baseUrl of ['https://producer.invalid', 'http://localhost:8123', 'http://[::1]:8123']) {
    const { client } = fixture({ '/search': { status: 'not_found', results: [] } }, baseUrl);
    await client.search('synthetic request');
  }
});
test('invalid code/hash selectors and unsupported workflows never fetch', async () => {
  const { client, calls } = fixture({});
  for (const value of ['../1.001146', `${C}?other=1`, 'https://evil.invalid', `${C}/profile`, '１.001146']) await assert.rejects(client.procedure(value), error(422, 'INVALID_REQUEST'));
  await assert.rejects(client.original(C, H.toUpperCase()), error(422, 'INVALID_REQUEST'));
  await assert.rejects(client.schema('1.003342', H), error(409, 'WORKFLOW_UNSUPPORTED'));
  await assert.rejects(client.schema(C, 'f'.repeat(64)), error(409, 'WORKFLOW_UNSUPPORTED'));
  assert.equal(calls.length, 0);
});
test('bounded search uses Python-compatible Unicode codepoint lengths', async () => {
  const { client } = fixture({ '/search': { status: 'not_found', results: [] } });
  await client.search('😀'.repeat(1000));
  await assert.rejects(client.search('😀'.repeat(1001)), error(422, 'INVALID_REQUEST'));
  await assert.rejects(client.search('  x  '), error(422, 'INVALID_REQUEST'));
  await assert.rejects(client.search('\u0001'.repeat(1000)), error(413, 'REQUEST_TOO_LARGE'));
});
test('malformed found statuses, duplicate codes and nonfinite scores fail closed', async () => {
  const a = { code: C, name: 'SYNTHETIC A', score: 1, matched_by: ['keyword'] };
  for (const value of [{ status: 'found', results: [] }, { status: 'not_found', results: [a] }, { status: 'found', results: [a, a] }, { status: 'found', results: [{ ...a, score: null }] }, { status: 'found', results: Array.from({ length: 6 }, () => a) }]) {
    await assert.rejects(fixture({ '/search': value }).client.search('synthetic request'), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  }
});
test('procedure preserves draft and blocked metadata, exact associations and rewrites only original route', async () => {
  const value = snapshot();
  value.analysis = { facts_ready: false, readiness: 'blocked' };
  const { client } = fixture({ [`/procedures/${C}`]: value });
  const result = await client.procedure(C);
  assert.deepEqual(result.analysis, value.analysis);
  assert.deepEqual(result.structured_profile, value.structured_profile);
  assert.equal((result.forms as JsonObject[])[0].original_download_url, `/api/discovery/procedures/${C}/forms/${H}/original`);
  assert.equal((value.forms as JsonObject[])[0].original_download_url, `/forms/${H}/original`);
});
test('snapshot, form and requirement association mismatches are rejected', async () => {
  const mutations = [
    (x: JsonObject) => { x.code = '1.003342'; },
    (x: JsonObject) => { x.procedure_code = '1.003342'; },
    (x: JsonObject) => { (x.forms as JsonObject[])[0].snapshot_id = 11; },
    (x: JsonObject) => { (x.requirements as JsonObject[])[0].form_ids = [99]; },
    (x: JsonObject) => { (x.requirements as JsonObject[])[0].snapshot_id = 11; },
    (x: JsonObject) => { (x.forms as JsonObject[])[0].original_download_url = 'https://evil.invalid/download'; },
    (x: JsonObject) => { x.source_url = 'javascript:alert(1)'; },
    (x: JsonObject) => { (x.forms as JsonObject[])[0].source_url = 'https://u:p@official.invalid/file'; },
  ];
  for (const mutate of mutations) { const value = snapshot(); mutate(value); await assert.rejects(fixture({ [`/procedures/${C}`]: value }).client.procedure(C), error(502, 'DISCOVERY_INVALID_RESPONSE')); }
});
test('profile relation hashes, exact source tuple membership and snapshot identity are validated', async () => {
  for (const mutate of [
    (p: JsonObject) => { ((p.profile as JsonObject).procedure_code as JsonObject).value = '1.003342'; },
    (p: JsonObject) => { ((p.profile as JsonObject).form_relationships as JsonObject[])[0].file_hash = 'f'.repeat(64); },
    (p: JsonObject) => { (p.sources as JsonObject[])[0].snapshot_id = 999; },
    (p: JsonObject) => { (p.sources as JsonObject[])[0].locator = 'another-location'; },
    (p: JsonObject) => { ((p.profile as JsonObject).form_relationships as JsonObject[])[0].field_schema_ref = '../../secret'; },
  ]) {
    const value = snapshot(); mutate(value.structured_profile as JsonObject);
    await assert.rejects(fixture({ [`/procedures/${C}`]: value }).client.procedure(C), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  }
});
test('structured profile matches current id, run, baseline and output hash; comparisons may cite other snapshots', async () => {
  const value = { ...envelope(), related_procedures: [], comparison_sources: [] };
  assert.deepEqual(await fixture({ [`/procedures/${C}`]: snapshot(), [`/procedures/${C}/profile`]: value }).client.profile(C), value);
  for (const key of ['id', 'run_id', 'baseline_id', 'output_sha256']) {
    const stale = clone(value) as JsonObject;
    stale[key] = key === 'id' ? 8 : key === 'run_id' ? 'synthetic-stale-run' : 'f'.repeat(64);
    await assert.rejects(fixture({ [`/procedures/${C}`]: snapshot(), [`/procedures/${C}/profile`]: stale }).client.profile(C), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  }
  const source = { ...(envelope().sources as JsonObject[])[0], source_id: '1.003342/primary', snapshot_id: 999 };
  const comparison = { ...value, comparison_sources: [source], related_procedures: [{ left_code: C, right_code: '1.003342', result: { source_refs: [{ source_id: source.source_id, locator: 'identity', quote: `SYNTHETIC procedure ${C}` }] } }] };
  await fixture({ [`/procedures/${C}`]: snapshot(), [`/procedures/${C}/profile`]: comparison }).client.profile(C);
});
test('unassociated originals and analyses stop before fetching the hash route', async () => {
  for (const operation of ['original', 'analysis'] as const) {
    const { client, calls } = fixture({ [`/procedures/${C}`]: snapshot() });
    await assert.rejects(client[operation](C, 'f'.repeat(64)), error(404, 'DISCOVERY_NOT_FOUND'));
    assert.equal(calls.length, 1);
  }
});
test('analysis distinguishes logical mapping from flattened database fields and checks hashes', async () => {
  const value = analysis();
  assert.deepEqual(await fixture({ [`/procedures/${C}`]: snapshot(), [`/forms/${H}/analysis`]: value }).client.analysis(C, H), value);
  for (const mutate of [(x: JsonObject) => { x.sha256 = 'f'.repeat(64); }, (x: JsonObject) => { (x.fields as JsonObject[])[0].form_sha256 = 'f'.repeat(64); }]) {
    const bad = analysis(); mutate(bad);
    await assert.rejects(fixture({ [`/procedures/${C}`]: snapshot(), [`/forms/${H}/analysis`]: bad }).client.analysis(C, H), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  }
});
test('original bytes are bounded attachments with exact SHA256, never returned URLs', async () => {
  const bytes = new TextEncoder().encode('SYNTHETIC ORIGINAL; not a government document');
  const sha = createHash('sha256').update(bytes).digest('hex');
  const { client, calls } = fixture({ [`/procedures/${C}`]: snapshot(sha), [`/forms/${sha}/original`]: () => new Response(bytes, { headers: { 'Content-Type': 'application/octet-stream', 'Content-Disposition': 'attachment; filename="synthetic-original.docx"' } }) });
  const result = await client.original(C, sha);
  assert.deepEqual(result.bytes, bytes); assert.equal(result.filename, `form-${sha}.bin`);
  assert.equal(result.contentType, 'application/octet-stream'); assert.equal(calls.length, 2);
  await assert.rejects(fixture({ [`/procedures/${C}`]: snapshot(sha), [`/forms/${sha}/original`]: () => new Response('changed synthetic bytes') }).client.original(C, sha), error(502, 'DISCOVERY_INVALID_RESPONSE'));
});
test('upstream filenames are ignored and active original content types are rejected', async () => {
  const bytes = new TextEncoder().encode('SYNTHETIC'); const sha = createHash('sha256').update(bytes).digest('hex');
  await assert.rejects(fixture({ [`/procedures/${C}`]: snapshot(sha), [`/forms/${sha}/original`]: () => new Response(bytes, { headers: { 'Content-Type': 'text/html' } }) }).client.original(C, sha), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  const result = await fixture({ [`/procedures/${C}`]: snapshot(sha), [`/forms/${sha}/original`]: () => new Response(bytes, { headers: { 'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'Content-Disposition': 'attachment; filename="../private.doc"' } }) }).client.original(C, sha);
  assert.equal(result.filename, `form-${sha}.docx`);
});
test('schema requires exact code/hash, readiness, analysis metadata and all 43 pinned field definitions', async () => {
  const routes = () => ({ [`/procedures/${C}`]: snapshot(), [`/forms/${H}/analysis`]: analysis(), [`/workflows/${C}/schema`]: schema() });
  assert.deepEqual(await fixture(routes()).client.schema(C, H), schema());
  const blocked = routes(); (blocked[`/procedures/${C}`] as JsonObject).analysis = { facts_ready: false };
  const pending = fixture(blocked);
  await assert.rejects(pending.client.schema(C, H), error(409, 'DISCOVERY_NOT_READY')); assert.equal(pending.calls.length, 1);
  for (const key of ['fields', 'fixed_values', 'revision', 'effective_from', 'review_status', 'procedure_code']) {
    const bad = routes(); (bad[`/workflows/${C}/schema`] as JsonObject)[key] = null;
    await assert.rejects(fixture(bad).client.schema(C, H), error(409, 'WORKFLOW_VERSION_MISMATCH'));
  }
  const changed = routes(); (changed[`/forms/${H}/analysis`] as JsonObject).mapping_metadata = { input_fingerprint: 'f'.repeat(64) };
  await assert.rejects(fixture(changed).client.schema(C, H), error(409, 'WORKFLOW_VERSION_MISMATCH'));
});
test('upstream statuses and exceptions expose stable codes without raw response bodies', async () => {
  for (const [status, expected, expectedCode] of [[404, 404, 'DISCOVERY_NOT_FOUND'], [409, 409, 'DISCOVERY_NOT_READY'], [429, 429, 'RATE_LIMITED'], [504, 504, 'DISCOVERY_TIMEOUT'], [500, 503, 'DISCOVERY_UNAVAILABLE'], [503, 503, 'DISCOVERY_UNAVAILABLE'], [302, 502, 'DISCOVERY_INVALID_RESPONSE']] as const) {
    const { client, calls } = fixture({ '/search': () => new Response('synthetic-private-provider-details', { status, headers: { 'Retry-After': '12' } }) });
    await assert.rejects(client.search('synthetic request'), error(expected, expectedCode)); assert.equal(calls.length, 1);
  }
  for (const name of ['Error', 'AbortError']) {
    const client = createDiscoveryClient({ workflow: workflow(), baseUrl: 'https://producer.invalid', fetch: (async () => { const failure = new Error('synthetic-private-dsn'); failure.name = name; throw failure; }) as typeof fetch });
    await assert.rejects(client.search('synthetic request'), error(name === 'AbortError' ? 504 : 503, name === 'AbortError' ? 'DISCOVERY_TIMEOUT' : 'DISCOVERY_UNAVAILABLE'));
  }
});
function streamed(chunks: Uint8Array[], headers: HeadersInit = { 'Content-Type': 'application/json' }) {
  let position = 0, cancelled = false;
  return { response: new Response(new ReadableStream<Uint8Array>({ pull(controller) { if (position < chunks.length) controller.enqueue(chunks[position++]); else controller.close(); }, cancel() { cancelled = true; } }, { highWaterMark: 0 }), { headers }), cancelled: () => cancelled, read: () => position };
}
test('JSON streamed size cap cancels before consuming tail even with forged Content-Length', async () => {
  const input = streamed([new Uint8Array(1024 * 1024), new Uint8Array(1), new Uint8Array(100)], { 'Content-Type': 'application/json', 'Content-Length': '1' });
  const { client } = fixture({ '/search': () => input.response });
  await assert.rejects(client.search('synthetic request'), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  assert.equal(input.cancelled(), true); assert.equal(input.read(), 2);
});
test('binary streamed size cap is ten MiB and cancels before consuming tail', async () => {
  const input = streamed([new Uint8Array(10 * 1024 * 1024), new Uint8Array(1), new Uint8Array(100)], { 'Content-Type': 'application/octet-stream' });
  const { client } = fixture({ [`/procedures/${C}`]: snapshot(), [`/forms/${H}/original`]: () => input.response });
  await assert.rejects(client.original(C, H), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  assert.equal(input.cancelled(), true); assert.equal(input.read(), 2);
});
test('JSON MIME, malformed JSON and invalid UTF-8 fail without leaking raw content', async () => {
  for (const response of [new Response('synthetic-private-json', { headers: { 'Content-Type': 'application/json' } }), new Response('{}', { headers: { 'Content-Type': 'text/html' } }), new Response(new Uint8Array([0xc3, 0x28]), { headers: { 'Content-Type': 'application/json' } })]) {
    await assert.rejects(fixture({ '/search': () => response }).client.search('synthetic request'), error(502, 'DISCOVERY_INVALID_RESPONSE'));
  }
});
test('thin chat forwards the exact validated contract and preserves citations; never routes from prose', async () => {
  const expected = chatFixture({ status: 'answered', answer: 'SYNTHETIC answer [synthetic-source]', citations: [{ id: 'synthetic-source', title: 'SYNTHETIC source', url: 'https://official.invalid/synthetic' }], model: 'synthetic-model' });
  const { client, calls } = fixture({ '/assistant/chat': expected });
  const body: DiscoveryChatRequest = { message: ' synthetic question ', procedure_code: null, history: [{ role: 'user', content: ' synthetic prior turn ' }] };
  assert.deepEqual(await client.chat(body), expected);
  assert.equal(calls.length, 1); assert.equal(calls[0].url, 'http://127.0.0.1:8123/assistant/chat');
  assert.deepEqual(JSON.parse(calls[0].init.body as string), { message: 'synthetic question', procedure_code: null, history: [{ role: 'user', content: 'synthetic prior turn' }] });
});
test('chat supports all producer status branches and does not invent missing citations', async () => {
  for (const status of ['insufficient_context', 'needs_clarification', 'out_of_scope']) {
    const expected = chatFixture({ status, answer: 'SYNTHETIC safe text', citations: [], model: null });
    assert.deepEqual(await fixture({ '/assistant/chat': expected }).client.chat({ message: 'synthetic request' }), expected);
  }
  for (const value of [
    { status: 'answered', answer: 'SYNTHETIC', citations: [], model: null },
    { status: 'bad', answer: 'SYNTHETIC', citations: [], model: null },
    { status: 'needs_clarification', answer: 'x'.repeat(16001), citations: [], model: null },
    { status: 'answered', answer: 'SYNTHETIC', citations: [{ id: 'x', title: 'Synthetic', url: 'javascript:evil' }], model: null },
    { status: 'answered', answer: 'SYNTHETIC', citations: [{ id: 'x', title: 'Synthetic', url: 'https://official.invalid' }, { id: 'x', title: 'Synthetic', url: 'https://official.invalid' }], model: null },
  ]) await assert.rejects(fixture({ '/assistant/chat': value }).client.chat({ message: 'synthetic request' }), error(502, 'DISCOVERY_INVALID_RESPONSE'));
});
test('chat request bounds, history roles, code and extra keys are checked before upstream', async () => {
  const { client, calls } = fixture({});
  for (const body of [{ message: 'x' }, { message: 'synthetic request', procedure_code: '../1.001146' }, { message: 'synthetic request', extra: true }, { message: 'synthetic request', history: [{ role: 'system', content: 'bad' }] }, { message: 'synthetic request', history: Array.from({ length: 13 }, () => ({ role: 'user', content: 'synthetic' })) }]) {
    await assert.rejects(client.chat(body as DiscoveryChatRequest), error(422, 'INVALID_REQUEST'));
  }
  assert.equal(calls.length, 0);
});
test('chat Python codepoint limits allow multibyte history up to the independent byte cap', async () => {
  const expected = chatFixture({ status: 'insufficient_context', answer: 'SYNTHETIC', citations: [], model: null });
  const { client } = fixture({ '/assistant/chat': expected });
  await client.chat({ message: '😀'.repeat(1000), history: [{ role: 'user', content: '😀'.repeat(16000) }] });
  await assert.rejects(client.chat({ message: 'synthetic request', history: [{ role: 'user', content: '😀'.repeat(16001) }] }), error(422, 'INVALID_REQUEST'));
});
