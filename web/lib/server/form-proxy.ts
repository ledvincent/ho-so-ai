import 'server-only';
import { apiUrl, privateHeaders, sameOriginJson } from './api';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';
import { isLocalProvider } from '../local-auth-policy';
import { verifiedSession } from './session';

export async function proxyDemoForm(request: Request, format: 'preview' | 'pdf') {
  if (!sameOriginJson(request)) return Response.json({ code: 'REQUEST_REJECTED' }, { status: 403, headers: privateHeaders });
  try {
    const authorization: Record<string, string> = {};
    if (isLocalProvider()) {
      const session = await verifiedSession();
      if (session.status !== 'signed-in') return Response.json({ code: session.status === 'signed-out' ? 'UNAUTHENTICATED' : 'AUTH_UNAVAILABLE' }, { status: session.status === 'signed-out' ? 401 : 503, headers: privateHeaders });
      authorization.Authorization = `Bearer ${session.token}`;
    }
    const body = await readRequestBody(request);
    const upstream = await fetch(apiUrl(`/v1/forms/demo/${format}`), { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: request.headers.get('origin') ?? '', ...authorization }, body, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(20000) });
    const headers = new Headers(privateHeaders);
    headers.set('Content-Type', upstream.headers.get('content-type') ?? 'application/json');
    if (upstream.ok && format === 'pdf') headers.set('Content-Disposition', 'attachment; filename="ho-so-ai-synthetic-review.pdf"');
    return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers });
  } catch (error) {
    if (error instanceof BodyTooLargeError) return Response.json({ code: 'REQUEST_TOO_LARGE' }, { status: 413, headers: privateHeaders });
    if (error instanceof InvalidRequestBodyError) return Response.json({ code: 'INVALID_REQUEST_BODY' }, { status: 400, headers: privateHeaders });
    return Response.json({ code: 'RENDERER_UNAVAILABLE' }, { status: 503, headers: privateHeaders });
  }
}
