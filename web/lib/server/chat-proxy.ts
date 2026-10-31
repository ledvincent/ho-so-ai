import 'server-only';
import { verifiedSession } from './session';
import { apiUrl, privateHeaders, sameOriginJson } from './api';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';

export async function proxyChat(request: Request, action: 'schema' | 'assist') {
  const session = await verifiedSession();
  if (session.status !== 'signed-in') return Response.json({ detail: { code: session.status === 'signed-out' ? 'UNAUTHENTICATED' : 'AUTH_UNAVAILABLE' } }, { status: session.status === 'signed-out' ? 401 : 503, headers: privateHeaders });
  if (action === 'assist' && !sameOriginJson(request)) return Response.json({ detail: { code: 'ORIGIN_FORBIDDEN' } }, { status: 403, headers: privateHeaders });
  try {
    const body = action === 'assist' ? await readRequestBody(request, 16384) : undefined;
    const upstream = await fetch(apiUrl(`/v1/chat/${action}`), { method: action === 'assist' ? 'POST' : 'GET', body, headers: { Authorization: `Bearer ${session.token}`, 'Content-Type': 'application/json', ...(action === 'assist' ? { Origin: request.headers.get('origin') ?? '' } : {}) }, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(25000) });
    return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers: { ...privateHeaders, 'Content-Type': 'application/json', ...(upstream.status === 429 ? { 'Retry-After': '60' } : {}) } });
  } catch (error) {
    const timedOut = error instanceof Error && ['TimeoutError', 'AbortError'].includes(error.name);
    const status = error instanceof BodyTooLargeError ? 413 : error instanceof InvalidRequestBodyError ? 400 : timedOut ? 504 : 503;
    return Response.json({ detail: { code: status === 413 ? 'REQUEST_TOO_LARGE' : status === 400 ? 'INVALID_REQUEST' : status === 504 ? 'ASSISTANT_TIMEOUT' : 'ASSISTANT_UNAVAILABLE' } }, { status, headers: privateHeaders });
  }
}
