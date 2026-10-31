import { createHash } from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { isIP } from 'node:net';

export type JsonObject = Record<string, unknown>;
export type DiscoveryChatRequest = {
  message: string;
  procedure_code?: string | null;
  history?: { role: 'user' | 'assistant'; content: string }[];
};
export type DiscoveryOriginal = { bytes: Uint8Array; contentType: string; filename: string };
export type DiscoveryClient = {
  search(query: string): Promise<JsonObject>;
  procedure(code: string): Promise<JsonObject>;
  profile(code: string): Promise<JsonObject>;
  analysis(code: string, sha: string): Promise<JsonObject>;
  original(code: string, sha: string): Promise<DiscoveryOriginal>;
  schema(code: string, sha: string): Promise<JsonObject>;
  chat(body: DiscoveryChatRequest): Promise<JsonObject>;
};

const CODE = /^[0-9]\.[0-9]{6}$/;
const SHA = /^[a-f0-9]{64}$/;
const SUPPORTED_CODE = '1.001146';
const SUPPORTED_SHA = 'a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751';
const JSON_LIMIT = 1024 * 1024;
const ORIGINAL_LIMIT = 10 * 1024 * 1024;
const UPSTREAM_TIMEOUT = 20_000;
const CHAT_TIMEOUT = 65_000;

export class DiscoveryError extends Error {
  constructor(public readonly status: number, public readonly code: string, public readonly retryAfter?: string) {
    super(code);
    this.name = 'DiscoveryError';
  }
}

function invalid(): never { throw new DiscoveryError(502, 'DISCOVERY_INVALID_RESPONSE'); }
function requestInvalid(): never { throw new DiscoveryError(422, 'INVALID_REQUEST'); }
function object(value: unknown): JsonObject {
  if (!value || typeof value !== 'object' || Array.isArray(value)) invalid();
  return value as JsonObject;
}
function array(value: unknown): unknown[] { if (!Array.isArray(value)) invalid(); return value; }
function string(value: unknown, max = 1_000_000): string {
  if (typeof value !== 'string' || value.length === 0 || [...value].length > max) invalid();
  return value;
}
function id(value: unknown): number { if (!Number.isSafeInteger(value) || (value as number) < 1) invalid(); return value as number; }
function hash(value: unknown): string { const result = string(value, 64); if (!SHA.test(result)) invalid(); return result; }
function code(value: unknown, input = false): string {
  if (typeof value !== 'string' || !CODE.test(value)) { if (input) requestInvalid(); invalid(); }
  return value;
}
function inputHash(value: unknown): string { if (typeof value !== 'string' || !SHA.test(value)) requestInvalid(); return value; }
function same(left: unknown, right: unknown): void { if (!isDeepStrictEqual(left, right)) invalid(); }
function safeUrl(value: unknown): string {
  const text = string(value, 8000);
  if (/[\u0000-\u0020\u007f\\]/u.test(text) || !/^https?:\/\//iu.test(text)) invalid();
  try {
    const url = new URL(text);
    if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password || /@/u.test(text.split('/').slice(0, 3).join('/'))) invalid();
  } catch { invalid(); }
  return text;
}
function relativeMetadata(value: unknown): void {
  if (value == null) return;
  const path = string(value, 2000);
  if (/^[\/\\]|[\\\u0000-\u0020\u007f:?#]/u.test(path) || path.split('/').some(part => !part || part === '.' || part === '..')) invalid();
}
function visit(value: unknown, callback: (node: JsonObject) => void, depth = 0): void {
  if (depth > 40) invalid();
  if (Array.isArray(value)) value.forEach(item => visit(item, callback, depth + 1));
  else if (value && typeof value === 'object') {
    const node = value as JsonObject;
    callback(node);
    Object.values(node).forEach(item => visit(item, callback, depth + 1));
  }
}
function sourceLinks(value: unknown): void {
  visit(value, node => {
    for (const [key, item] of Object.entries(node)) {
      if (key === 'original_download_url') continue; // checked against its exact association separately
      if ((key === 'url' || key.endsWith('_url')) && item != null) safeUrl(item);
      if (key === 'field_schema_ref') relativeMetadata(item);
    }
  });
}
function origin(baseUrl: string | undefined): string {
  if (!baseUrl || baseUrl !== baseUrl.trim() || /[\u0000-\u0020\u007f\\@]/u.test(baseUrl)) throw new DiscoveryError(503, 'DISCOVERY_UNAVAILABLE');
  try {
    const url = new URL(baseUrl);
    const loopback = url.hostname === 'localhost' || url.hostname === '[::1]' || (isIP(url.hostname) === 4 && url.hostname.startsWith('127.'));
    if (!(url.protocol === 'https:' || (url.protocol === 'http:' && loopback)) || url.username || url.password || url.pathname !== '/' || url.search || url.hash) throw new Error();
    return url.origin;
  } catch { throw new DiscoveryError(503, 'DISCOVERY_UNAVAILABLE'); }
}
function upstreamError(response: Response): never {
  if (response.status === 404) throw new DiscoveryError(404, 'DISCOVERY_NOT_FOUND');
  if (response.status === 409) throw new DiscoveryError(409, 'DISCOVERY_NOT_READY');
  if (response.status === 429) {
    const supplied = response.headers.get('retry-after') ?? '';
    throw new DiscoveryError(429, 'RATE_LIMITED', /^[0-9]{1,4}$/u.test(supplied) && Number(supplied) <= 3600 ? supplied : '60');
  }
  if (response.status === 504) throw new DiscoveryError(504, 'DISCOVERY_TIMEOUT');
  if (response.status === 413) throw new DiscoveryError(413, 'REQUEST_TOO_LARGE');
  if (response.status === 400 || response.status === 422) throw new DiscoveryError(response.status, 'INVALID_REQUEST');
  if (response.status >= 300 && response.status < 400) invalid();
  throw new DiscoveryError(503, 'DISCOVERY_UNAVAILABLE');
}

type SourceRegistry = Map<string, JsonObject>;
function sources(value: unknown): SourceRegistry {
  const registry: SourceRegistry = new Map();
  for (const entry of array(value)) {
    const source = object(entry);
    const key = JSON.stringify([string(source.source_id, 200), string(source.locator, 2000)]);
    if (registry.has(key)) invalid();
    safeUrl(source.url); hash(source.sha256); id(source.snapshot_id);
    string(source.text); string(source.kind, 100); string(source.fetched_at, 100);
    registry.set(key, source);
  }
  return registry;
}
function citations(value: unknown, registry: SourceRegistry): void {
  const normalise = (text: string) => text.replace(/\s+/gu, ' ').trim();
  visit(value, node => {
    if ('source_id' in node && 'locator' in node && 'quote' in node) {
      const source = registry.get(JSON.stringify([string(node.source_id, 200), string(node.locator, 2000)]));
      const quote = normalise(string(node.quote));
      if (!source || !quote || !normalise(string(source.text)).includes(quote)) invalid();
    }
  });
}
function profileEnvelope(value: unknown, snapshot: JsonObject): JsonObject {
  const envelope = object(value);
  id(envelope.id); string(envelope.run_id, 200); hash(envelope.baseline_id); hash(envelope.output_sha256);
  object(envelope.metadata);
  const profile = object(envelope.profile);
  same(object(profile.procedure_code).value, snapshot.code);
  const knownHashes = new Set(array(snapshot.forms).map(item => object(item).form_sha256).filter(item => item != null));
  const relationships = array(profile.form_relationships).map(object);
  const relatedHashes = relationships.map(item => hash(item.file_hash));
  if (new Set(relatedHashes).size !== relatedHashes.length || knownHashes.size !== relatedHashes.length || relatedHashes.some(item => !knownHashes.has(item))) invalid();
  relationships.forEach(item => relativeMetadata(item.field_schema_ref));
  const registry = sources(envelope.sources);
  const primary = registry.get(JSON.stringify(['primary', 'identity']));
  if (!primary || primary.snapshot_id !== snapshot.id || primary.sha256 !== snapshot.sha256) invalid();
  citations(profile, registry);
  sourceLinks(envelope);
  return envelope;
}
function validateProcedure(value: unknown, selectedCode: string): JsonObject {
  const result = object(value);
  same(result.code, selectedCode); same(result.procedure_code, selectedCode);
  const snapshotId = id(result.id);
  hash(result.sha256); safeUrl(result.source_url); string(result.fetched_at, 100); string(result.name, 2000);
  const forms = array(result.forms).map(object);
  const formIds = new Set<number>();
  const rewritten = forms.map(form => {
    const formId = id(form.id);
    if (formIds.has(formId) || form.snapshot_id !== snapshotId) invalid();
    formIds.add(formId); safeUrl(form.source_url);
    const sha = form.form_sha256 == null ? null : hash(form.form_sha256);
    const download = form.original_download_url;
    if (download != null && (sha === null || download !== `/forms/${sha}/original`)) invalid();
    if (form.linked_from != null) {
      const provenance = object(form.linked_from);
      same(provenance.source_url, result.source_url); same(provenance.sha256, result.sha256); same(provenance.fetched_at, result.fetched_at);
    }
    return { ...form, original_download_url: download == null ? null : `/api/discovery/procedures/${selectedCode}/forms/${sha}/original` };
  });
  for (const key of ['requirements', 'facts', 'methods', 'fees']) {
    const rows = array(result[key]);
    const seen = new Set<number>();
    for (const entry of rows) {
      const row = object(entry);
      const rowId = id(row.id);
      if (seen.has(rowId) || row.snapshot_id !== snapshotId) invalid();
      seen.add(rowId);
      same(row.source_url, result.source_url); same(row.sha256, result.sha256); same(row.fetched_at, result.fetched_at);
      if (key === 'requirements') {
        const ids = array(row.form_ids).map(id);
        if (new Set(ids).size !== ids.length || ids.some(item => !formIds.has(item))) invalid();
      }
    }
  }
  sourceLinks(result);
  if (result.structured_profile != null) profileEnvelope(result.structured_profile, result);
  return { ...result, forms: rewritten };
}
function associated(snapshot: JsonObject, sha: string): JsonObject[] {
  const matches = array(snapshot.forms).map(object).filter(form => form.form_sha256 === sha);
  if (!matches.length) throw new DiscoveryError(404, 'DISCOVERY_NOT_FOUND');
  return matches;
}
function validateAnalysis(value: unknown, sha: string, forms: JsonObject[]): JsonObject {
  const result = object(value);
  same(result.sha256, sha);
  string(result.review_status, 50);
  for (const form of forms) for (const key of ['review_status', 'revision_reference', 'issued_on', 'effective_from', 'pdf_path']) {
    if (key in form) same(result[key], form[key]);
  }
  for (const entry of array(result.fields)) {
    const field = object(entry);
    same(field.form_sha256, sha); string(field.field_id, 500);
  }
  if (result.fields_json != null) array(result.fields_json).forEach(item => string(object(item).id, 500));
  sourceLinks(result);
  return result;
}
function filename(contentType: string, sha: string): string {
  const extensions: Record<string, string> = {
    'application/pdf': 'pdf', 'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/octet-stream': 'bin', 'application/rtf': 'rtf', 'application/vnd.oasis.opendocument.text': 'odt',
  };
  return `form-${sha}.${extensions[contentType]}`;
}

/** Pure server consumer; the server-only wrapper supplies configuration and workflow. */
export function createDiscoveryClient(options: { baseUrl?: string; fetch?: typeof fetch; workflow: JsonObject }): DiscoveryClient {
  const fetcher = options.fetch ?? globalThis.fetch;
  // Copy caller-owned metadata so a later mutation cannot change the workflow gate.
  const workflow = structuredClone(options.workflow);

  async function request(path: string, settings: { body?: unknown; binary?: boolean; chat?: boolean } = {}) {
    const base = origin(options.baseUrl); // lazy failure: an unconfigured app can still start
    if (!/^\/search$|^\/assistant\/chat$|^\/procedures\/[0-9]\.[0-9]{6}(?:\/profile)?$|^\/forms\/[a-f0-9]{64}\/(?:analysis|original)$|^\/workflows\/1\.001146\/schema$/u.test(path)) requestInvalid();
    const controller = new AbortController();
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const cancel = () => { void reader?.cancel().catch(() => undefined); };
    const limit = settings.binary ? ORIGINAL_LIMIT : JSON_LIMIT;
    const task = async () => {
      const response = await fetcher(base + path, {
        method: settings.body === undefined ? 'GET' : 'POST',
        headers: settings.body === undefined ? { Accept: settings.binary ? 'application/octet-stream' : 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
        ...(settings.body === undefined ? {} : { body: JSON.stringify(settings.body) }),
        signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error',
      });
      if (response.redirected || (response.status >= 300 && response.status < 400)) { void response.body?.cancel().catch(() => undefined); invalid(); }
      if (response.status !== 200) { void response.body?.cancel().catch(() => undefined); upstreamError(response); }
      const contentType = response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() ?? '';
      if (!settings.binary && contentType !== 'application/json') { void response.body?.cancel().catch(() => undefined); invalid(); }
      const declared = response.headers.get('content-length');
      if (declared && (!/^[0-9]+$/u.test(declared) || Number(declared) > limit)) { void response.body?.cancel().catch(() => undefined); invalid(); }
      const chunks: Uint8Array[] = [];
      let total = 0;
      if (response.body) {
        reader = response.body.getReader();
        while (true) {
          const chunk = await reader.read();
          if (chunk.done) break;
          total += chunk.value.byteLength;
          if (total > limit) { cancel(); invalid(); }
          chunks.push(chunk.value);
        }
      }
      const bytes = new Uint8Array(total);
      let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
      if (settings.binary) return { bytes, response };
      try { return { json: object(JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes))) }; }
      catch { invalid(); }
    };
    try {
      return await Promise.race([task(), new Promise<never>((_, reject) => {
        timer = setTimeout(() => { controller.abort(); cancel(); reject(new DiscoveryError(504, 'DISCOVERY_TIMEOUT')); }, settings.chat ? CHAT_TIMEOUT : UPSTREAM_TIMEOUT);
      })]);
    } catch (error) {
      cancel();
      if (error instanceof DiscoveryError) throw error;
      if (controller.signal.aborted || (error instanceof Error && ['AbortError', 'TimeoutError'].includes(error.name))) throw new DiscoveryError(504, 'DISCOVERY_TIMEOUT');
      throw new DiscoveryError(503, 'DISCOVERY_UNAVAILABLE');
    } finally { if (timer) clearTimeout(timer); }
  }
  async function json(path: string, settings?: { body?: unknown; chat?: boolean }): Promise<JsonObject> {
    const result = await request(path, settings);
    if (!('json' in result) || !result.json) invalid();
    return result.json;
  }
  async function procedure(selectedCode: string): Promise<JsonObject> {
    code(selectedCode, true);
    return validateProcedure(await json(`/procedures/${selectedCode}`), selectedCode);
  }
  async function analysis(selectedCode: string, sha: string): Promise<JsonObject> {
    code(selectedCode, true); inputHash(sha);
    const snapshot = await procedure(selectedCode);
    const forms = associated(snapshot, sha);
    return validateAnalysis(await json(`/forms/${sha}/analysis`), sha, forms);
  }
  return {
    async search(query) {
      if (typeof query !== 'string' || [...query.trim()].length < 2 || [...query.trim()].length > 1000) requestInvalid();
      const body = { query: query.trim() };
      if (Buffer.byteLength(JSON.stringify(body)) > 4096) throw new DiscoveryError(413, 'REQUEST_TOO_LARGE');
      const result = await json('/search', { body });
      if (!['found', 'not_found'].includes(string(result.status, 20))) invalid();
      const results = array(result.results);
      if (results.length > 5 || (result.status === 'found') !== (results.length > 0)) invalid();
      const seen = new Set<string>();
      for (const item of results) {
        const match = object(item), matchCode = code(match.code);
        string(match.name, 2000);
        if (seen.has(matchCode) || typeof match.score !== 'number' || !Number.isFinite(match.score) || typeof match.similarity !== 'number' || !Number.isFinite(match.similarity)) invalid();
        seen.add(matchCode);
      }
      return { status: result.status, results: results.map(item => {
        const match = object(item);
        return { code: match.code, name: match.name, score: match.score, similarity: match.similarity };
      }) };
    },
    procedure,
    async profile(selectedCode) {
      const snapshot = await procedure(selectedCode);
      if (snapshot.structured_profile == null) throw new DiscoveryError(404, 'DISCOVERY_NOT_FOUND');
      const result = profileEnvelope(await json(`/procedures/${selectedCode}/profile`), snapshot);
      const head = object(snapshot.structured_profile);
      for (const key of ['id', 'run_id', 'baseline_id', 'output_sha256']) same(result[key], head[key]);
      const comparisonRegistry = sources(result.comparison_sources);
      for (const entry of array(result.related_procedures)) {
        const comparison = object(entry);
        const left = code(comparison.left_code), right = code(comparison.right_code);
        if (left === right || ![left, right].includes(selectedCode)) invalid();
        citations(comparison.result, comparisonRegistry);
      }
      return result;
    },
    analysis,
    async original(selectedCode, sha) {
      code(selectedCode, true); inputHash(sha);
      associated(await procedure(selectedCode), sha);
      const result = await request(`/forms/${sha}/original`, { binary: true });
      if (!('bytes' in result) || !result.bytes || !result.response || !result.bytes.length) invalid();
      if (createHash('sha256').update(result.bytes).digest('hex') !== sha) invalid();
      const type = result.response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() ?? 'application/octet-stream';
      if (!['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/octet-stream', 'application/rtf', 'application/vnd.oasis.opendocument.text'].includes(type)) invalid();
      return { bytes: result.bytes, contentType: type, filename: filename(type, sha) };
    },
    async schema(selectedCode, sha) {
      code(selectedCode, true); inputHash(sha);
      if (selectedCode !== SUPPORTED_CODE || sha !== SUPPORTED_SHA) throw new DiscoveryError(409, 'WORKFLOW_UNSUPPORTED');
      if (workflow.procedure_code !== SUPPORTED_CODE || workflow.form_sha256 !== SUPPORTED_SHA || !Array.isArray(workflow.fields) || workflow.fields.length !== 43 || !isDeepStrictEqual(workflow.fixed_values, { request_type: 'stay_extension' })) throw new DiscoveryError(409, 'WORKFLOW_VERSION_MISMATCH');
      const snapshot = await procedure(selectedCode);
      const forms = associated(snapshot, sha);
      if (!snapshot.analysis || object(snapshot.analysis).facts_ready !== true) throw new DiscoveryError(409, 'DISCOVERY_NOT_READY');
      const metadata = validateAnalysis(await json(`/forms/${sha}/analysis`), sha, forms);
      for (const key of ['review_status', 'revision_reference', 'issued_on', 'effective_from', 'pdf_path', 'mapping_metadata']) {
        if (!isDeepStrictEqual(metadata[key], workflow[key])) throw new DiscoveryError(409, 'WORKFLOW_VERSION_MISMATCH');
      }
      const result = await json(`/workflows/${SUPPORTED_CODE}/schema`);
      if (result.procedure_code !== selectedCode || !isDeepStrictEqual(result.fields, workflow.fields) || !isDeepStrictEqual(result.fixed_values, workflow.fixed_values) || result.revision !== workflow.revision_reference || result.effective_from !== workflow.effective_from || result.review_status !== workflow.review_status) throw new DiscoveryError(409, 'WORKFLOW_VERSION_MISMATCH');
      sourceLinks(result);
      return result;
    },
    async chat(body) {
      if (!body || typeof body !== 'object' || Array.isArray(body)) requestInvalid();
      const input = body as JsonObject;
      if (Object.keys(input).some(key => !['message', 'procedure_code', 'history'].includes(key)) || typeof input.message !== 'string' || [...input.message.trim()].length < 2 || [...input.message.trim()].length > 1000) requestInvalid();
      if (input.procedure_code != null) code(input.procedure_code, true);
      const history = input.history ?? [];
      if (!Array.isArray(history) || history.length > 12) requestInvalid();
      const turns = history.map(item => {
        if (!item || typeof item !== 'object' || Array.isArray(item)) requestInvalid();
        const turn = item as JsonObject;
        if (Object.keys(turn).some(key => !['role', 'content'].includes(key)) || !['user', 'assistant'].includes(turn.role as string) || typeof turn.content !== 'string' || [...turn.content.trim()].length < 1 || [...turn.content.trim()].length > 8000) requestInvalid();
        return { role: turn.role, content: turn.content.trim() };
      });
      const payload = { message: input.message.trim(), ...(input.procedure_code === undefined ? {} : { procedure_code: input.procedure_code }), history: turns };
      if (Buffer.byteLength(JSON.stringify(payload)) > 400 * 1024) throw new DiscoveryError(413, 'REQUEST_TOO_LARGE');
      const result = await json('/assistant/chat', { body: payload, chat: true });
      if (Object.keys(result).some(key => !['status', 'answer', 'citations', 'model'].includes(key))) invalid();
      if (!['answered', 'insufficient_context', 'needs_clarification', 'out_of_scope'].includes(string(result.status, 30))) invalid();
      if (!string(result.answer, 16000).trim()) invalid();
      const refs = array(result.citations), ids = new Set<string>();
      if (refs.length > 20 || (result.status === 'answered' && refs.length === 0) || (result.status === 'out_of_scope' && refs.length !== 0)) invalid();
      for (const item of refs) {
        const citation = object(item), key = string(citation.id, 64);
        if (Object.keys(citation).some(field => !['id', 'title', 'url'].includes(field)) || !/^[A-Za-z0-9_-]+$/u.test(key) || ids.has(key)) invalid();
        ids.add(key); string(citation.title, 500); safeUrl(citation.url);
      }
      if (result.model != null) string(result.model, 256);
      return result;
    },
  };
}
