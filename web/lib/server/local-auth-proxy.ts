import 'server-only';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { apiUrl, privateHeaders, sameOriginJson } from './api';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';
import { identityFrom, isLocalProvider, localOrigin, localCookieOptions, LOCAL_COOKIE, validSessionToken } from '../local-auth-policy';
import { lookupLocalSession } from './local-session';

const failure = (code: string, status: number, retryAfter?: string | null) => NextResponse.json({ detail: { code } }, { status, headers: { ...privateHeaders, ...(retryAfter && /^\d{1,5}$/.test(retryAfter) ? { 'Retry-After': retryAfter } : {}) } });
function cookieOptions() {
  return localCookieOptions();
}
function clearCookie(response: NextResponse) {
  response.cookies.set(LOCAL_COOKIE, '', { ...cookieOptions(), expires: new Date(0), maxAge: 0 });
  return response;
}
export async function login(request: Request) {
  if (!isLocalProvider()) return failure('AUTH_UNAVAILABLE', 503);
  try { localOrigin(); } catch { return failure('AUTH_UNAVAILABLE', 503); }
  if (!sameOriginJson(request)) return failure('ORIGIN_FORBIDDEN', 403);
  try {
    const body = await readRequestBody(request, 2048);
    const upstream = await fetch(apiUrl('/v1/auth/login'), { method: 'POST', body, headers: { 'Content-Type': 'application/json', Origin: request.headers.get('origin') ?? '' }, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000) });
    if (!upstream.ok) {
      const status = [400, 401, 403, 422, 429].includes(upstream.status) ? upstream.status : 503;
      return failure(status === 401 ? 'INVALID_CREDENTIALS' : status === 429 ? 'RATE_LIMITED' : status === 403 ? 'ORIGIN_FORBIDDEN' : status === 503 ? 'AUTH_UNAVAILABLE' : 'INVALID_REQUEST', status, upstream.headers.get('retry-after'));
    }
    const data: unknown = await upstream.json();
    const identity = identityFrom(data);
    const token = data && typeof data === 'object' ? (data as Record<string, unknown>).session_token : null;
    if (!identity || !validSessionToken(token)) return failure('AUTH_UNAVAILABLE', 503);
    const response = NextResponse.json(identity, { headers: privateHeaders });
    response.cookies.set(LOCAL_COOKIE, token, { ...cookieOptions(), expires: new Date(identity.expires_at * 1000) });
    return response;
  } catch (error) {
    if (error instanceof BodyTooLargeError) return failure('REQUEST_TOO_LARGE', 413);
    if (error instanceof InvalidRequestBodyError) return failure('INVALID_REQUEST', 400);
    return failure('AUTH_UNAVAILABLE', 503);
  }
}
export async function session() {
  if (!isLocalProvider()) return failure('AUTH_UNAVAILABLE', 503);
  const result = await lookupLocalSession((await cookies()).get(LOCAL_COOKIE)?.value);
  if (result.status !== 'signed-in') return failure(result.status === 'signed-out' ? 'UNAUTHENTICATED' : 'AUTH_UNAVAILABLE', result.status === 'signed-out' ? 401 : 503);
  return NextResponse.json({ user: result.user, expires_at: result.expires_at }, { headers: privateHeaders });
}
export async function logout(request: Request) {
  if (!isLocalProvider()) return failure('AUTH_UNAVAILABLE', 503);
  try { localOrigin(); } catch { return failure('AUTH_UNAVAILABLE', 503); }
  if (!sameOriginJson(request)) return failure('ORIGIN_FORBIDDEN', 403);
  try {
    const body = await readRequestBody(request, 256);
    const parsed = JSON.parse(body);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object' || Object.keys(parsed).length) return failure('INVALID_REQUEST', 422);
    const token = (await cookies()).get(LOCAL_COOKIE)?.value;
    if (!validSessionToken(token)) return clearCookie(NextResponse.json({ ok: true }, { headers: privateHeaders }));
    const upstream = await fetch(apiUrl('/v1/auth/logout'), { method: 'POST', body: '{}', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', Origin: request.headers.get('origin') ?? '' }, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(5000) });
    return clearCookie(upstream.ok || upstream.status === 401 ? NextResponse.json({ ok: true }, { headers: privateHeaders }) : failure('LOGOUT_UNCONFIRMED', 503));
  } catch { return clearCookie(failure('LOGOUT_UNCONFIRMED', 503)); }
}
