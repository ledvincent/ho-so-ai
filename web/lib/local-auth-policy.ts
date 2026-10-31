/** Pure policy shared by server handlers and proxy; no credentials in client code. */
export const LOCAL_COOKIE = 'hoso_local_session';
export function isLocalProvider(): boolean { return process.env.HOSO_AUTH_PROVIDER === 'local'; }
export function validSessionToken(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{40,256}$/.test(value);
}
export function localOrigin(): URL {
  const url = new URL(process.env.HOSO_PUBLIC_ORIGIN ?? '');
  if (!['http:', 'https:'].includes(url.protocol) || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)
      || url.origin !== process.env.HOSO_PUBLIC_ORIGIN || url.username || url.password) throw new Error('Local configuration unavailable');
  return url;
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
