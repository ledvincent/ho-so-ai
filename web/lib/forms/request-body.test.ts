import test from 'node:test';
import assert from 'node:assert/strict';
import { BodyTooLargeError, InvalidRequestBodyError, readRequestBody } from '../request-body';

const encode = (value: string) => new TextEncoder().encode(value);

function streamedRequest(chunks: Uint8Array[], headers: HeadersInit = {}) {
  let next = 0;
  let cancelled = false;
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      if (next === chunks.length) controller.close();
      else controller.enqueue(chunks[next++]);
    },
    cancel() { cancelled = true; },
  }, { highWaterMark: 0 });
  const request = new Request('http://localhost/api/example', {
    method: 'POST', body: stream, headers, duplex: 'half',
  } as RequestInit & { duplex: 'half' });
  return { request, cancelled: () => cancelled, chunksRead: () => next };
}

test('a chunked body without Content-Length is cancelled before reading beyond the limit', async () => {
  const input = streamedRequest([encode('a'.repeat(4096)), encode('b'.repeat(4096)), encode('x'), encode('unread tail')]);
  assert.equal(input.request.headers.has('content-length'), false);
  await assert.rejects(readRequestBody(input.request), BodyTooLargeError);
  assert.equal(input.cancelled(), true);
  assert.equal(input.chunksRead(), 3);
});

test('a spoofed small Content-Length does not bypass the actual byte limit', async () => {
  const input = streamedRequest([encode('a'.repeat(8193)), encode('unread tail')], { 'Content-Length': '1' });
  await assert.rejects(readRequestBody(input.request), BodyTooLargeError);
  assert.equal(input.cancelled(), true);
  assert.equal(input.chunksRead(), 1);
});

test('exactly 8192 bytes are accepted without cancellation', async () => {
  const expected = 'a'.repeat(8192);
  const input = streamedRequest([encode(expected.slice(0, 4096)), encode(expected.slice(4096))]);
  assert.equal(await readRequestBody(input.request), expected);
  assert.equal(input.cancelled(), false);
});

test('Unicode limits use UTF-8 bytes and preserve characters split between chunks', async () => {
  const encoded = encode('ắ');
  const split = streamedRequest([encoded.slice(0, 1), encoded.slice(1)]);
  assert.equal(await readRequestBody(split.request, 3), 'ắ');
  const tooLarge = streamedRequest([encoded]);
  await assert.rejects(readRequestBody(tooLarge.request, 2), BodyTooLargeError);
  assert.equal(tooLarge.cancelled(), true);
});

test('invalid UTF-8 cancels the stream and returns only a sanitized error', async () => {
  const input = streamedRequest([new Uint8Array([0xc3, 0x28]), encode('unread tail')]);
  await assert.rejects(readRequestBody(input.request), (error: unknown) => {
    assert.ok(error instanceof InvalidRequestBodyError);
    assert.equal(error.message, 'Request body could not be read as UTF-8.');
    return true;
  });
  assert.equal(input.cancelled(), true);
  assert.equal(input.chunksRead(), 1);
});

test('incomplete UTF-8 at the end and stream failures do not expose body data', async () => {
  const incomplete = streamedRequest([new Uint8Array([0xc3])]);
  await assert.rejects(readRequestBody(incomplete.request), InvalidRequestBodyError);
  const broken = new Request('http://localhost/api/example', {
    method: 'POST',
    body: new ReadableStream({ start(controller) { controller.error(new Error('private body details')); } }),
    duplex: 'half',
  } as RequestInit & { duplex: 'half' });
  await assert.rejects(readRequestBody(broken), (error: unknown) => {
    assert.ok(error instanceof InvalidRequestBodyError);
    assert.equal(error.message.includes('private'), false);
    return true;
  });
});
