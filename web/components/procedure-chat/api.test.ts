import test from 'node:test';
import assert from 'node:assert/strict';
import { createDiscoveryAdapter, readAnswer, readSearch, safeSourceUrl } from './api';
import type { LocalSession } from '@/components/guided-portal/api';

const session: LocalSession = { user: { id: 'fictional-local-user', username: 'fixture', identity_provider: 'local' }, expires_at: 1900000000 };
test('assistant prose is not a structured selection; answered output requires safe citations', () => {
  const answer = { status: 'answered', answer: 'Perhaps 1.001146', citations: [{ id: 'source-a', title: 'Source', url: 'https://example.test/source' }], model: null };
  assert.equal(readAnswer(answer).answer, answer.answer);
  assert.throws(() => readSearch(answer));
  assert.throws(() => readAnswer({ ...answer, citations: [] }));
  assert.equal(safeSourceUrl('javascript:alert(1)'), false);
});
test('search mapping retains exact names/codes and ignores score as selection authority', () => {
  const result = readSearch({ status: 'found', results: [{ code: '1.003342', name: 'Visa issuance', score: 999, similarity: .99 }] });
  assert.deepEqual(result.candidates, [{ code: '1.003342', name: 'Visa issuance' }]);
  assert.equal(readSearch({ status: 'not_found', results: [] }).candidates.length, 0);
});
test('chat omits procedure before confirmation and pins it on a confirmed follow-up', async () => {
  const bodies: any[] = [];
  const fetcher = async (path: any, init?: RequestInit) => {
    if (path === '/api/auth/session') return Response.json(session);
    bodies.push(JSON.parse(String(init?.body)));
    return Response.json({ status: 'needs_clarification', answer: 'Please clarify.', citations: [], model: null });
  };
  const adapter = createDiscoveryAdapter(session, fetcher as typeof fetch); const signal = new AbortController().signal;
  await adapter.chat('A new visa', [], null, signal);
  await adapter.chat('Which originals?', [], '1.003342', signal);
  assert.equal(Object.hasOwn(bodies[0], 'procedure_code'), false);
  assert.equal(bodies[1].procedure_code, '1.003342');
});
