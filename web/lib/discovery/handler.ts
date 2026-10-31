/** Server route policy. Dependencies are supplied only by the server composition root. */
import { createHash } from 'node:crypto';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';
import { isAllowedMutation } from '../request-policy';
import { DiscoveryError, type DiscoveryChatRequest } from './upstream';

type Session = { status: 'signed-in'; subject: string } | { status: 'signed-out' | 'unconfigured' };
type Client = {
  search(query: string): Promise<unknown>;
  chat(body: DiscoveryChatRequest): Promise<unknown>;
  procedure(code: string): Promise<unknown>;
  profile(code: string): Promise<unknown>;
  analysis(code: string, hash: string): Promise<unknown>;
  schema(code: string, hash: string): Promise<unknown>;
  original(code: string, hash: string): Promise<{ bytes: Uint8Array; contentType: string; filename: string }>;
};
type Action = 'search' | 'chat' | 'procedure' | 'profile' | 'analysis' | 'schema' | 'original';
type Route = { action: Action; code?: string; hash?: string; method: 'GET' | 'POST' };
const privateHeaders = { 'Cache-Control': 'private, no-store', Pragma: 'no-cache', 'X-Content-Type-Options': 'nosniff' };
const codePattern = /^\d\.\d{6}$/;
const hashPattern = /^[a-f0-9]{64}$/;
const localSubjectPattern = /^local:[a-f0-9]{32}:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;

function errorResponse(status: number, code: string) {
  return Response.json({ detail: { code } }, { status, headers: { ...privateHeaders, ...(status === 429 ? { 'Retry-After': '60' } : {}) } });
}
function resolveRoute(parts: string[]): Route {
  if (parts.length === 1 && ['search', 'chat'].includes(parts[0])) return { action: parts[0] as 'search' | 'chat', method: 'POST' };
  if (parts[0] !== 'procedures' || !codePattern.test(parts[1] ?? '')) throw new DiscoveryError(404, 'DISCOVERY_NOT_FOUND');
  const code = parts[1];
  if (parts.length === 2) return { action: 'procedure', code, method: 'GET' };
  if (parts.length === 3 && parts[2] === 'profile') return { action: 'profile', code, method: 'GET' };
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
  if (!record(value) || Object.keys(value).some((key) => !['message', 'procedure_code', 'history'].includes(key))) throw new DiscoveryError(422, 'INVALID_REQUEST');
  const message = text(value.message, 2, 1000);
  const code = value.procedure_code;
  if (code !== undefined && code !== null && (typeof code !== 'string' || !codePattern.test(code))) throw new DiscoveryError(422, 'INVALID_REQUEST');
  const history = value.history ?? [];
  if (!Array.isArray(history) || history.length > 12 || value.history === null) throw new DiscoveryError(422, 'INVALID_REQUEST');
  const turns = history.map((turn) => {
    if (!record(turn) || Object.keys(turn).some((key) => !['role', 'content'].includes(key)) || typeof turn.role !== 'string' || !['user', 'assistant'].includes(turn.role)) throw new DiscoveryError(422, 'INVALID_REQUEST');
    return { role: turn.role as 'user' | 'assistant', content: text(turn.content, 1, 8000) };
  });
  return { message, ...(code !== undefined ? { procedure_code: code as string | null } : {}), history: turns };
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
  limit: (subject: string, action: Action) => void;
}) {
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
          (provider === 'local' && !['localhost', '127.0.0.1', '[::1]'].includes(origin.hostname))) throw new Error();
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
        const raw = await readRequestBody(request, route.action === 'chat' ? 400 * 1024 : 4096);
        let value: unknown;
        try { value = JSON.parse(raw); } catch { return errorResponse(400, 'INVALID_REQUEST'); }
        if (!record(value)) return errorResponse(422, 'INVALID_REQUEST');
        body = value;
      }
      let result: unknown;
      switch (route.action) {
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
