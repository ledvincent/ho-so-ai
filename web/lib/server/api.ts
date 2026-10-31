import 'server-only';
import { isAllowedMutation } from '../request-policy';
export const privateHeaders = { 'Cache-Control': 'private, no-store', 'Pragma': 'no-cache' };
export function apiUrl(path: string): string {
  const base = process.env.HOSO_API_URL ?? 'http://127.0.0.1:8000';
  const url = new URL(base);
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Invalid API configuration');
  if (url.username || url.password || url.hash || url.search) throw new Error('Invalid API configuration');
  if (process.env.HOSO_AUTH_PROVIDER === 'local' && !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname)) throw new Error('Local API must be loopback');
  return new URL(path, url).toString();
}
export function sameOriginJson(request: Request): boolean {
  return isAllowedMutation(request, process.env.HOSO_PUBLIC_ORIGIN || (process.env.HOSO_AUTH_PROVIDER === 'local' ? '' : 'http://127.0.0.1:3000'));
}
