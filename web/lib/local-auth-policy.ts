/** Pure policy shared by server handlers and proxy; no credentials in client code. */
export const LOCAL_COOKIE = 'hoso_local_session';
export function isLocalProvider(): boolean { return process.env.HOSO_AUTH_PROVIDER === 'local'; }
export function validSessionToken(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{40,256}$/.test(value);
}
export function localOrigin(): URL {
  const url = new URL(process.env.HOSO_PUBLIC_ORIGIN ?? '');
  const mode = process.env.HOSO_DEPLOYMENT_MODE ?? 'local';
  const loopback = ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname);
  const publicHost = url.hostname.length <= 253 && url.hostname.includes('.') && !url.hostname.endsWith('.localhost')
    && !/^\d+\.\d+\.\d+\.\d+$/.test(url.hostname)
    && url.hostname.split('.').every((label) => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label));
  const allowed = mode === 'local' ? ['http:', 'https:'].includes(url.protocol) && loopback
    : mode === 'hosted-demo' && url.protocol === 'https:' && !loopback && publicHost
      && (process.env.HOSO_LOCAL_DEMO_SEED ?? 'false') === 'false';
  if (!allowed || url.origin !== process.env.HOSO_PUBLIC_ORIGIN || url.username || url.password) throw new Error('Local configuration unavailable');
  return url;
}
export function localCookieOptions() {
  return { httpOnly: true, secure: localOrigin().protocol === 'https:', sameSite: 'lax' as const, path: '/' };
}
export function isPrivatePage(path: string): boolean {
  if (path === '/demo/login' || path === '/login' || path.startsWith('/sign-in')) return false;
  return ['/portal', '/workspace', '/chat', '/forms', '/research', '/documents', '/demo'].some((prefix) => path === prefix || path.startsWith(prefix + '/'));
}
export type LocalIdentity = { user: { id: string; username: string; identity_provider: 'local' }; expires_at: number };
export function identityFrom(value: unknown): LocalIdentity | null {
  if (!value || typeof value !== 'object') return null;
  const data = value as Record<string, unknown>;
  if (!data.user || typeof data.user !== 'object') return null;
  const user = data.user as Record<string, unknown>;
  if (typeof user.id !== 'string' || !user.id || user.id.length > 256 || typeof user.username !== 'string'
      || !/^[a-zA-Z0-9_.-]{1,64}$/.test(user.username) || user.identity_provider !== 'local'
      || typeof data.expires_at !== 'number' || !Number.isSafeInteger(data.expires_at)
      || data.expires_at <= Math.floor(Date.now() / 1000)) return null;
  return { user: { id: user.id, username: user.username, identity_provider: 'local' }, expires_at: data.expires_at };
}
