import { verifiedSession } from '@/lib/server/session';
import { apiUrl, privateHeaders, sameOriginJson } from '@/lib/server/api';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '@/lib/request-body';

export const dynamic = 'force-dynamic';
async function forward(request: Request, method: 'GET' | 'PUT') {
  const session = await verifiedSession();
  if (session.status !== 'signed-in') return Response.json({ code: session.status === 'unconfigured' ? 'AUTH_UNAVAILABLE' : 'UNAUTHENTICATED' }, { status: session.status === 'unconfigured' ? 503 : 401, headers: privateHeaders });
  if (method === 'PUT' && !sameOriginJson(request)) return Response.json({ code: 'REQUEST_REJECTED' }, { status: 403, headers: privateHeaders });
  try {
    const body = method === 'PUT' ? await readRequestBody(request) : undefined;
    const upstream = await fetch(apiUrl('/v1/profile'), { method, body, headers: { Authorization: `Bearer ${session.token}`, 'Content-Type': 'application/json', ...(method === 'PUT' ? { Origin: request.headers.get('origin') ?? '' } : {}) }, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(10000) });
    return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers: { ...privateHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    if (error instanceof BodyTooLargeError) return Response.json({ code: 'REQUEST_TOO_LARGE' }, { status: 413, headers: privateHeaders });
    if (error instanceof InvalidRequestBodyError) return Response.json({ code: 'INVALID_REQUEST_BODY' }, { status: 400, headers: privateHeaders });
    return Response.json({ code: 'PROFILE_UNAVAILABLE' }, { status: 503, headers: privateHeaders });
  }
}
export function GET(request: Request) { return forward(request, 'GET'); }
export function PUT(request: Request) { return forward(request, 'PUT'); }
