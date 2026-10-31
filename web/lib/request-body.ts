/** Read a small UTF-8 request body without trusting Content-Length. */
export class BodyTooLargeError extends Error {
  constructor() { super('Request body exceeds the configured limit.'); this.name = 'BodyTooLargeError'; }
}

export class InvalidRequestBodyError extends Error {
  constructor() { super('Request body could not be read as UTF-8.'); this.name = 'InvalidRequestBodyError'; }
}

async function cancelReader(reader: ReadableStreamDefaultReader<Uint8Array>): Promise<void> {
  try { await reader.cancel(); } catch { /* Never expose the underlying stream error. */ }
}

export async function readRequestBody(request: Request, maxBytes = 8192): Promise<string> {
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 0) throw new RangeError('Invalid body limit.');
  if (!request.body) return '';
  const reader = request.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  const parts: string[] = [];
  let bytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > maxBytes) {
        await cancelReader(reader);
        throw new BodyTooLargeError();
      }
      parts.push(decoder.decode(value, { stream: true }));
    }
    parts.push(decoder.decode());
    return parts.join('');
  } catch (error) {
    if (error instanceof BodyTooLargeError) throw error;
    await cancelReader(reader);
    throw new InvalidRequestBodyError();
  } finally {
    reader.releaseLock();
  }
}
