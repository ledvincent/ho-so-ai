import 'server-only';
import { isAllowedMutation } from '../request-policy';
export const privateHeaders = { 'Cache-Control': 'private, no-store', 'Pragma': 'no-cache' };
export function apiUrl(path: string): string {
  const base = process.env.HOSO_API_URL ?? 'http://127.0.0.1:8000';
  const url = new URL(base);
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('Invalid API configuration');
  return new URL(path, url).toString();
}
export function sameOriginJson(request: Request): boolean {
  return isAllowedMutation(request, process.env.HOSO_PUBLIC_ORIGIN || 'http://127.0.0.1:3000');
}
