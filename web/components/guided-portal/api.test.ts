import test from 'node:test';
import assert from 'node:assert/strict';
import { createGuidedAdapter, type LocalSession } from './api';
import { emptyValues } from '@/components/na5-demo/model';

const identity: LocalSession = { user: { id: 'fictional-account-a', username: 'fictional', identity_provider: 'local' }, expires_at: 1900000000 };
const input = () => ({ message: 'My full name is Fictional Nguyen', values: emptyValues(), revision: 7, focusField: 'applicant_full_name', history: [], signal: new AbortController().signal });
const version = '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3';
function fake(options: { wrongRevision?: boolean; switched?: boolean; status?: number; invalidField?: boolean } = {}) {
  const calls: { path: string; body: Record<string, unknown> | null }[] = []; let sessions = 0;
  const fetcher = async (path: string | URL | Request, init?: RequestInit) => {
    const body = init?.body ? JSON.parse(String(init.body)) : null; calls.push({ path: String(path), body });
    if (String(path) === '/api/auth/session') { sessions += 1; return Response.json(options.switched && sessions > 1 ? { ...identity, user: { ...identity.user, id: 'fictional-account-b' } } : identity); }
    if (options.status) return Response.json({ detail: { code: 'ASSISTANT_UNAVAILABLE' } }, { status: options.status });
    return Response.json({ request_id: body.request_id, draft_revision: options.wrongRevision ? 6 : body.draft_revision, procedure_code: '1.001146', schema_version: version, review_status: 'draft', status: 'proposed', assistant_text: 'What is your sex?', proposed_changes: [{ field_id: options.invalidField ? 'applicant_signature' : 'applicant_full_name', value: 'Fictional Nguyen' }], next_field: 'sex' });
  };
  return { calls, fetcher: fetcher as typeof fetch };
}

test('consumer sends exact CHAT-01 request, applies validated proposal and never saves profile', async () => {
  const mock = fake(); const reply = await createGuidedAdapter(identity, mock.fetcher)(input());
  assert.equal(reply.values.applicant_full_name, 'FICTIONAL NGUYEN');
  const call = mock.calls.find(item => item.path === '/api/chat/assist')!;
  assert.deepEqual(Object.keys(call.body!).sort(), ['request_id', 'draft_revision', 'procedure_code', 'intent', 'message', 'focus_field', 'values'].sort());
  assert.equal(call.body!.draft_revision, 7); assert.equal(call.body!.focus_field, 'applicant_full_name');
  assert.equal(mock.calls.some(item => item.path === '/api/profile'), false);
});
test('mismatched revision and manual signature proposals are rejected', async () => {
  await assert.rejects(createGuidedAdapter(identity, fake({ wrongRevision: true }).fetcher)(input()));
  await assert.rejects(createGuidedAdapter(identity, fake({ invalidField: true }).fetcher)(input()));
});
test('account switch while model responds expires the UI instead of applying data', async () => {
  await assert.rejects(createGuidedAdapter(identity, fake({ switched: true }).fetcher)(input()), { name: 'SessionExpired' });
});
test('401 expires the UI; provider failure has no retry or draft/profile write', async () => {
  await assert.rejects(createGuidedAdapter(identity, fake({ status: 401 }).fetcher)(input()), { name: 'SessionExpired' });
  const mock = fake({ status: 503 }); await assert.rejects(createGuidedAdapter(identity, mock.fetcher)(input()));
  assert.equal(mock.calls.filter(item => item.path === '/api/chat/assist').length, 1);
});
