/** Compare against deployment configuration, never a proxy-rewritten request URL. */
export function isAllowedMutation(request: Request, publicOrigin: string): boolean {
  try {
    const expected = new URL(publicOrigin);
    if (!['http:', 'https:'].includes(expected.protocol) || expected.origin !== publicOrigin) return false;
    return request.headers.get('origin') === publicOrigin &&
      request.headers.get('content-type')?.split(';')[0].trim().toLowerCase() === 'application/json';
  } catch { return false; }
}
