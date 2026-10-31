import 'server-only';
import { verifiedSession } from './session';
import { apiUrl, privateHeaders, sameOriginJson } from './api';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';

const failure = (status: number, code: string) => Response.json({ detail: { code } }, { status, headers: privateHeaders });

export async function proxyProfileV2(request: Request, action: 'read' | 'write' | 'prefill') {
  try {
    const session = await verifiedSession();
    if (session.status !== 'signed-in') return failure(session.status === 'signed-out' ? 401 : 503, session.status === 'signed-out' ? 'UNAUTHENTICATED' : 'AUTH_UNAVAILABLE');
    if (new URL(request.url).search) return failure(400, 'INVALID_REQUEST');
    if (action !== 'read' && !sameOriginJson(request)) return failure(403, 'ORIGIN_FORBIDDEN');
    const site = request.headers.get('sec-fetch-site');
    const origin = request.headers.get('origin');
    if ((site && !['same-origin', 'none'].includes(site)) || (origin && origin !== process.env.HOSO_PUBLIC_ORIGIN)) return failure(403, 'ORIGIN_FORBIDDEN');
    const body = action === 'read' ? undefined : await readRequestBody(request, 16384);
    const upstream = await fetch(apiUrl(action === 'prefill' ? '/v2/profile/prefill' : '/v2/profile'), {
      method: action === 'read' ? 'GET' : action === 'write' ? 'PUT' : 'POST', body,
      headers: { Authorization: `Bearer ${session.token}`, 'Content-Type': 'application/json', ...(action === 'read' ? {} : { Origin: origin ?? '' }) },
      cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(10000),
    });
    // Only this owned API's known statuses/JSON cross the versioned boundary.
    if (![200, 400, 401, 403, 404, 409, 413, 422, 429, 503].includes(upstream.status)
      || upstream.headers.get('content-type')?.split(';')[0] !== 'application/json') return failure(503, 'PROFILE_UNAVAILABLE');
    const responseBody = await readRequestBody(new Request('http://profile-response.invalid', {
      method: 'POST', body: upstream.body, duplex: 'half',
    } as RequestInit), 65536);
    return new Response(responseBody, { status: upstream.status, headers: { ...privateHeaders, 'Content-Type': 'application/json' } });
  } catch (error) {
    if (error instanceof BodyTooLargeError) return failure(413, 'REQUEST_TOO_LARGE');
    if (error instanceof InvalidRequestBodyError) return failure(400, 'INVALID_REQUEST_BODY');
    return failure(503, 'PROFILE_UNAVAILABLE');
  }
}
