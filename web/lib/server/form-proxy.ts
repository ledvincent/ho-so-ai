import 'server-only';
import { apiUrl, privateHeaders, sameOriginJson } from './api';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';

export async function proxyDemoForm(request: Request, format: 'preview' | 'pdf') {
  if (!sameOriginJson(request)) return Response.json({ code: 'REQUEST_REJECTED' }, { status: 403, headers: privateHeaders });
  try {
    const body = await readRequestBody(request);
    const upstream = await fetch(apiUrl(`/v1/forms/demo/${format}`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body, cache: 'no-store', signal: AbortSignal.timeout(20000) });
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
