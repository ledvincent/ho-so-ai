/** Server route policy. Dependencies are supplied only by the server composition root. */
import { createHash } from 'node:crypto';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';
import { isAllowedMutation } from '../request-policy';
import { DiscoveryError, type DiscoveryChatRequest } from './upstream';

type Session = { status: 'signed-in'; subject: string } | { status: 'signed-out' | 'unconfigured' };
type Client = {
  setup(): Promise<unknown>;
  documents(code: string): Promise<unknown>;
  documentSchema(id: string): Promise<unknown>;
  documentTemplate(id: string): Promise<Attachment>;
  documentPages(id: string): Promise<unknown>;
  documentValidate(id: string, body: DocumentValues): Promise<unknown>;
  documentPreview(id: string, body: DocumentValues, pages: boolean): Promise<{ data?: unknown; bytes?: Uint8Array; contentType: string; reviewToken: string }>;
  documentDownload(id: string, body: DocumentDownload): Promise<Attachment>;
  search(query: string): Promise<unknown>;
  chat(body: DiscoveryChatRequest): Promise<unknown>;
  procedure(code: string): Promise<unknown>;
  profile(code: string): Promise<unknown>;
  analysis(code: string, hash: string): Promise<unknown>;
  schema(code: string, hash: string): Promise<unknown>;
  original(code: string, hash: string): Promise<{ bytes: Uint8Array; contentType: string; filename: string }>;
};
type Attachment = { bytes: Uint8Array; contentType: string; filename: string };
type DocumentValues = { values: Record<string, string>; template_version: string };
type DocumentDownload = DocumentValues & { review_token: string; confirmed: true };
type Action = 'setup' | 'documents' | 'documentSchema' | 'documentTemplate' | 'documentPages' | 'documentValidate' | 'documentPreview' | 'documentPreviewPages' | 'documentDownload' | 'search' | 'chat' | 'procedure' | 'profile' | 'analysis' | 'schema' | 'original';
type Route = { action: Action; code?: string; hash?: string; id?: string; method: 'GET' | 'POST' };
const privateHeaders = { 'Cache-Control': 'private, no-store', Pragma: 'no-cache', 'X-Content-Type-Options': 'nosniff' };
const codePattern = /^\d\.\d{6}$/;
const hashPattern = /^[a-f0-9]{64}$/;
const localSubjectPattern = /^local:[a-f0-9]{32}:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;

function errorResponse(status: number, code: string) {
  return Response.json({ detail: { code } }, { status, headers: { ...privateHeaders, ...(status === 429 ? { 'Retry-After': '60' } : {}) } });
}
function resolveRoute(parts: string[]): Route {
  if (parts.length === 1 && parts[0] === 'setup') return { action: 'setup', method: 'GET' };
  if (parts.length === 1 && ['search', 'chat'].includes(parts[0])) return { action: parts[0] as 'search' | 'chat', method: 'POST' };
  if (parts.length === 3 && parts[0] === 'documents' && /^[a-z0-9][a-z0-9_-]{0,99}$/.test(parts[1])) {
    const routes: Record<string, { action: Action; method: 'GET' | 'POST' }> = {
      schema: { action: 'documentSchema', method: 'GET' }, template: { action: 'documentTemplate', method: 'GET' },
      'template-pages': { action: 'documentPages', method: 'GET' }, validate: { action: 'documentValidate', method: 'POST' },
      preview: { action: 'documentPreview', method: 'POST' }, 'preview-pages': { action: 'documentPreviewPages', method: 'POST' },
      download: { action: 'documentDownload', method: 'POST' },
    };
    if (Object.hasOwn(routes, parts[2])) return { ...routes[parts[2]], id: parts[1] };
  }
  if (parts[0] !== 'procedures' || !codePattern.test(parts[1] ?? '')) throw new DiscoveryError(404, 'DISCOVERY_NOT_FOUND');
  const code = parts[1];
  if (parts.length === 2) return { action: 'procedure', code, method: 'GET' };
  if (parts.length === 3 && parts[2] === 'profile') return { action: 'profile', code, method: 'GET' };
  if (parts.length === 3 && parts[2] === 'documents') return { action: 'documents', code, method: 'GET' };
  if (parts.length === 5 && parts[2] === 'forms' && hashPattern.test(parts[3]) && ['analysis', 'schema', 'original'].includes(parts[4])) {
    return { action: parts[4] as 'analysis' | 'schema' | 'original', code, hash: parts[3], method: 'GET' };
  }
  throw new DiscoveryError(404, 'DISCOVERY_NOT_FOUND');
}
function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}
function text(value: unknown, min: number, max: number): string {
  if (typeof value !== 'string') throw new DiscoveryError(422, 'INVALID_REQUEST');
  const trimmed = value.trim();
  // Count Unicode code points as the producer's Python string limits do.
  if ([...trimmed].length < min || [...trimmed].length > max || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(trimmed)) throw new DiscoveryError(422, 'INVALID_REQUEST');
  return trimmed;
}
export function chatRequest(value: unknown): DiscoveryChatRequest {
  if (!record(value) || Object.keys(value).some((key) => !['message', 'procedure_code', 'history', 'retrieval_state', 'clarification_answer'].includes(key))) throw new DiscoveryError(422, 'INVALID_REQUEST');
  const message = text(value.message, 2, 1000);
  const code = value.procedure_code;
  if (code !== undefined && code !== null && (typeof code !== 'string' || !codePattern.test(code))) throw new DiscoveryError(422, 'INVALID_REQUEST');
  const history = value.history ?? [];
  if (!Array.isArray(history) || history.length > 12 || value.history === null) throw new DiscoveryError(422, 'INVALID_REQUEST');
  const turns = history.map((turn) => {
    if (!record(turn) || Object.keys(turn).some((key) => !['role', 'content'].includes(key)) || typeof turn.role !== 'string' || !['user', 'assistant'].includes(turn.role)) throw new DiscoveryError(422, 'INVALID_REQUEST');
    return { role: turn.role as 'user' | 'assistant', content: text(turn.content, 1, 16000) };
  });
  const state = value.retrieval_state;
  const answer = value.clarification_answer;
  // State is opaque: validate its envelope without decoding or changing bytes.
  if (state !== undefined && state !== null && (typeof state !== 'string' || state.length > 12000 || /[\u0000-\u0020\u007f]/.test(state))) throw new DiscoveryError(422, 'INVALID_REQUEST');
  if (answer !== undefined && answer !== null && (typeof answer !== 'string' || [...answer].length > 1000 || /[\u0000-\u001f\u007f]/.test(answer))) throw new DiscoveryError(422, 'INVALID_REQUEST');
  if (answer && (!state || code)) throw new DiscoveryError(422, 'INVALID_REQUEST');
  return { message, ...(code !== undefined ? { procedure_code: code as string | null } : {}), history: turns,
    ...(state !== undefined ? { retrieval_state: state as string | null } : {}),
    ...(answer !== undefined ? { clarification_answer: answer as string | null } : {}) };
}

export function documentRequest(value: unknown, download = false): DocumentValues | DocumentDownload {
  const allowed = download ? ['values', 'template_version', 'review_token', 'confirmed'] : ['values', 'template_version'];
  if (!record(value) || Object.keys(value).some((key) => !allowed.includes(key)) || !record(value.values)
      || Object.keys(value.values).length > 2000 || typeof value.template_version !== 'string' || !hashPattern.test(value.template_version)) throw new DiscoveryError(422, 'INVALID_REQUEST');
  const values: Record<string, string> = {};
  for (const [key, item] of Object.entries(value.values)) {
    if (!/^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$/.test(key) || ['__proto__', 'prototype', 'constructor'].includes(key)
        || typeof item !== 'string' || [...item].length > 16000
        || /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(item)) throw new DiscoveryError(422, 'INVALID_REQUEST');
    values[key] = item;
  }
  const base = { values, template_version: value.template_version };
  if (!download) return base;
  if (value.confirmed !== true || typeof value.review_token !== 'string' || !value.review_token
      || value.review_token.length > 131072 || /[\u0000-\u0020\u007f]/.test(value.review_token)) throw new DiscoveryError(422, 'INVALID_REQUEST');
  return { ...base, confirmed: true, review_token: value.review_token };
}

/** One process; only hashes retained. Restart/expiry requires a fresh preview. */
export function createReviewBindings(now: () => number = Date.now, capacity = 1024) {
  const bindings = new Map<string, { owner: string; document: string; version: string; values: string; until: number }>();
  const digest = (value: string) => createHash('sha256').update(value).digest('hex');
  const valuesDigest = (body: DocumentValues) => digest(JSON.stringify(Object.entries(body.values).sort(([a], [b]) => a.localeCompare(b))));
  const prune = () => { for (const [key, item] of bindings) if (item.until <= now()) bindings.delete(key); };
  return {
    issue(owner: string, document: string, body: DocumentValues, token: string) {
      prune();
      if (!token || token.length > 131072 || /[\u0000-\u0020\u007f]/.test(token)) throw new DiscoveryError(502, 'DISCOVERY_INVALID_RESPONSE');
      const key = digest(owner) + ':' + digest(token);
      if (!bindings.has(key) && bindings.size >= capacity) throw new DiscoveryError(429, 'RATE_LIMITED');
      bindings.set(key, { owner: digest(owner), document, version: body.template_version, values: valuesDigest(body), until: now() + 15 * 60000 });
    },
    verify(owner: string, document: string, body: DocumentDownload) {
      prune();
      const item = bindings.get(digest(owner) + ':' + digest(body.review_token));
      if (!item || item.owner !== digest(owner) || item.document !== document || item.version !== body.template_version || item.values !== valuesDigest(body)) throw new DiscoveryError(409, 'REVIEW_REQUIRED');
    },
  };
}

function attachmentResponse(attachment: Attachment, headers: Record<string, string> = {}) {
  if (!/^[A-Za-z0-9_.-]{1,120}$/.test(attachment.filename)) throw new DiscoveryError(502, 'DISCOVERY_INVALID_RESPONSE');
  return new Response(Uint8Array.from(attachment.bytes).buffer, { headers: { ...privateHeaders,
    'Content-Type': attachment.contentType, 'Content-Disposition': `attachment; filename="${attachment.filename}"`,
    'Content-Security-Policy': "sandbox; default-src 'none'", ...headers } });
}

/** Single-process checkpoint budget; stores only hashed subjects and counters. */
export function createRequestLimiter(now: () => number = Date.now, capacity = 1024) {
  const buckets = new Map<string, { until: number; total: number; search: number; chat: number }>();
  return (subject: string, action: Action) => {
    const current = now();
    for (const [key, bucket] of buckets) if (bucket.until <= current) buckets.delete(key);
    const key = createHash('sha256').update(subject).digest('hex');
    let bucket = buckets.get(key);
    if (!bucket) {
      if (buckets.size >= capacity) throw new DiscoveryError(429, 'RATE_LIMITED');
      bucket = { until: current + 60000, total: 0, search: 0, chat: 0 };
      buckets.set(key, bucket);
    }
    if (bucket.total >= 60 || (action === 'search' && bucket.search >= 12) || (action === 'chat' && bucket.chat >= 8)) throw new DiscoveryError(429, 'RATE_LIMITED');
    bucket.total += 1;
    if (action === 'search' || action === 'chat') bucket[action] += 1;
  };
}

export function createDiscoveryHandler(deps: {
  verifySession: () => Promise<Session>;
  client: () => Client;
  publicOrigin: () => string | undefined;
  provider: () => string | undefined;
  deploymentMode?: () => string | undefined;
  limit: (subject: string, action: Action) => void;
}) {
  const reviewBindings = createReviewBindings();
  return async (request: Request, parts: string[]): Promise<Response> => {
    try {
      let session: Session;
      try { session = await deps.verifySession(); } catch { return errorResponse(503, 'AUTH_UNAVAILABLE'); }
      if (session.status !== 'signed-in') return errorResponse(session.status === 'signed-out' ? 401 : 503, session.status === 'signed-out' ? 'UNAUTHENTICATED' : 'AUTH_UNAVAILABLE');
      const provider = deps.provider() ?? 'clerk';
      if (!session.subject || (provider !== 'clerk' && provider !== 'local') || (provider === 'local' && !localSubjectPattern.test(session.subject))) return errorResponse(503, 'AUTH_UNAVAILABLE');
      let origin: URL;
      const configured = deps.publicOrigin();
      try {
        origin = new URL(configured ?? '');
        if (!['http:', 'https:'].includes(origin.protocol) || origin.origin !== configured || origin.username || origin.password ||
          (provider === 'local' && (deps.deploymentMode?.() === 'hosted-demo'
            ? origin.protocol !== 'https:' || ['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname)
            : (deps.deploymentMode?.() !== undefined && deps.deploymentMode?.() !== 'local') || !['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname)))) throw new Error();
      } catch { return errorResponse(503, 'AUTH_UNAVAILABLE'); }
      const site = request.headers.get('sec-fetch-site');
      const suppliedOrigin = request.headers.get('origin');
      if ((site && !['same-origin', 'none'].includes(site)) || (suppliedOrigin !== null && suppliedOrigin !== origin.origin)) return errorResponse(403, 'ORIGIN_FORBIDDEN');
      if (new URL(request.url).search) return errorResponse(400, 'INVALID_REQUEST');
      const route = resolveRoute(parts);
      if (request.method !== route.method) return errorResponse(405, 'INVALID_REQUEST');
      if (route.method === 'POST' && !isAllowedMutation(request, origin.origin)) return errorResponse(403, 'ORIGIN_FORBIDDEN');
      deps.limit(session.subject, route.action);
      let body: Record<string, unknown> | undefined;
      if (route.method === 'POST') {
        const raw = await readRequestBody(request, route.action === 'chat' || route.id ? 1024 * 1024 : 4096);
        let value: unknown;
        try { value = JSON.parse(raw); } catch { return errorResponse(400, 'INVALID_REQUEST'); }
        if (!record(value)) return errorResponse(422, 'INVALID_REQUEST');
        body = value;
      }
      let result: unknown;
      switch (route.action) {
        case 'setup': result = await deps.client().setup(); break;
        case 'documents': result = await deps.client().documents(route.code!); break;
        case 'documentSchema': result = await deps.client().documentSchema(route.id!); break;
        case 'documentPages': result = await deps.client().documentPages(route.id!); break;
        case 'documentTemplate': return attachmentResponse(await deps.client().documentTemplate(route.id!));
        case 'documentValidate': result = await deps.client().documentValidate(route.id!, documentRequest(body)); break;
        case 'documentPreview':
        case 'documentPreviewPages': {
          const values = documentRequest(body);
          const preview = await deps.client().documentPreview(route.id!, values, route.action === 'documentPreviewPages');
          reviewBindings.issue(session.subject, route.id!, values, preview.reviewToken);
          const headers = { ...privateHeaders, 'X-Review-Token': preview.reviewToken };
          if (route.action === 'documentPreviewPages') return Response.json(preview.data, { headers });
          if (!preview.bytes || preview.contentType !== 'application/pdf') throw new DiscoveryError(502, 'DISCOVERY_INVALID_RESPONSE');
          return attachmentResponse({ bytes: preview.bytes, contentType: preview.contentType, filename: `${route.id}-preview.pdf` }, headers);
        }
        case 'documentDownload': {
          const values = documentRequest(body, true) as DocumentDownload;
          reviewBindings.verify(session.subject, route.id!, values);
          return attachmentResponse(await deps.client().documentDownload(route.id!, values));
        }
        case 'search': {
          if (!body || Object.keys(body).some((key) => key !== 'query')) return errorResponse(422, 'INVALID_REQUEST');
          const query = text(body.query, 2, 1000);
          result = await deps.client().search(query); break;
        }
        case 'chat': result = await deps.client().chat(chatRequest(body)); break;
        case 'procedure': result = await deps.client().procedure(route.code!); break;
        case 'profile': result = await deps.client().profile(route.code!); break;
        case 'analysis': result = await deps.client().analysis(route.code!, route.hash!); break;
        case 'schema': result = await deps.client().schema(route.code!, route.hash!); break;
        case 'original': {
          const attachment = await deps.client().original(route.code!, route.hash!);
          if (!/^[A-Za-z0-9_.-]{1,120}$/.test(attachment.filename)) throw new DiscoveryError(502, 'DISCOVERY_INVALID_RESPONSE');
          // Copy to a concrete ArrayBuffer for the Web Response body contract.
          return new Response(Uint8Array.from(attachment.bytes).buffer, { headers: { ...privateHeaders,
            'Content-Type': attachment.contentType, 'Content-Disposition': `attachment; filename="${attachment.filename}"`,
            'Content-Security-Policy': "sandbox; default-src 'none'", ETag: `"${route.hash}"` } });
        }
      }
      return Response.json(result, { headers: privateHeaders });
    } catch (error) {
      if (error instanceof DiscoveryError) return errorResponse(error.status, error.code);
      if (error instanceof BodyTooLargeError) return errorResponse(413, 'REQUEST_TOO_LARGE');
      if (error instanceof InvalidRequestBodyError) return errorResponse(400, 'INVALID_REQUEST');
      return errorResponse(503, 'DISCOVERY_UNAVAILABLE');
    }
  };
}
