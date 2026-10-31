import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyValues } from '@/components/na5-demo/model';
import type { LocalSession } from '@/components/guided-portal/api';
import { createProfileClient, ProfileError } from './api';
import { emptyDetails } from './fields';
import { NA5_CODE, NA5_FORM } from '@/components/procedure-chat/model';
import type { PrefillContext } from './prefill-model';

const session: LocalSession = { user: { id: 'fixture-a', username: 'fixture', identity_provider: 'local' }, expires_at: 1900000000 };
const context: PrefillContext = { session: 'fixture-a:1900000000', document: 'exact-tuple:epoch1', procedureCode: NA5_CODE, formSha: NA5_FORM, schemaVersion: '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3', draftRevision: 4 };
const record = () => ({ schema_version: 'profile.v2', profile_id: 'fixture-profile-a', revision: 3, details: { ...emptyDetails(), basics: { ...emptyDetails().basics, full_legal_name: 'Fictional Person' }, passport: { ...emptyDetails().passport, document_number: '000012345' } }, legacy: { nationality: 'Ambiguous legacy value', address: null } });
function seam(change?: (path: string, body: any, result: any) => Response | undefined) {
  const calls: { path: string; init?: RequestInit }[] = [];
  const fetcher = async (path: any, init?: RequestInit) => {
    calls.push({ path, init });
    if (path === '/api/auth/session') return change?.(path, null, session) ?? Response.json(session);
    const body = init?.body ? JSON.parse(String(init.body)) : null;
    const result = path === '/api/profile/v2/prefill' ? { ...body, profile_id: 'fixture-profile-a', profile_revision: 3, review_status: 'draft', proposals: [{ proposal_id: 'name', source_fields: ['basics.full_legal_name'], source_values: { 'basics.full_legal_name': 'Fictional Person' }, target_field: 'applicant_full_name', value: 'FICTIONAL PERSON', mapping: 'uppercase', existing_value: body.values.applicant_full_name ?? null, requires_overwrite: Boolean(body.values.applicant_full_name && body.values.applicant_full_name !== 'FICTIONAL PERSON') }], unmapped: [{ source_field: 'legacy.nationality', reason: 'legacy_meaning_ambiguous' }] } : record();
    return change?.(path, body, result) ?? Response.json(result);
  };
  return { calls, client: createProfileClient(session, fetcher as typeof fetch) };
}
test('creating a profile client performs zero reads; consented load sends only current draft/context to deterministic own endpoint', async () => {
  const { calls, client } = seam(); assert.equal(calls.length, 0);
  const source = await client.prefill.load(context, emptyValues(), new AbortController().signal);
  assert.equal(source.profileId, 'fixture-profile-a'); assert.equal(source.rows[0].value, 'FICTIONAL PERSON');
  const requests = calls.filter(call => call.path !== '/api/auth/session');
  assert.deepEqual(requests.map(call => [call.path, call.init?.method]), [['/api/profile/v2', 'GET'], ['/api/profile/v2/prefill', 'POST']]);
  const body = JSON.parse(String(requests[1].init?.body));
  assert.equal(body.consent, true); assert.equal(body.applicant_confirmed, true); assert.equal(body.expected_revision, 3); assert.equal(body.draft_revision, 4);
  assert.deepEqual(body.values, emptyValues());
  assert.equal(Object.hasOwn(body, 'details'), false); assert.equal(Object.hasOwn(body, 'profile_id'), false);
  assert.ok(calls.every(call => call.init?.credentials === 'same-origin' && call.init.cache === 'no-store'));
  assert.ok(calls.every(call => !/discovery|assist|model/.test(call.path)));
});
test('preapply check reads revision again without generating proposals or writing', async () => {
  const { calls, client } = seam((path, _, result) => path === '/api/profile/v2' ? Response.json({ ...result, revision: 4 }) : undefined);
  assert.deepEqual(await client.prefill.check(new AbortController().signal), { profileId: 'fixture-profile-a', profileRevision: 4 });
  assert.deepEqual(calls.filter(call => call.path !== '/api/auth/session').map(call => [call.path, call.init?.method]), [['/api/profile/v2', 'GET']]);
});
test('all echoed context and source/profile values must match; typed equal values still produce locked proposals later', async () => {
  for (const patch of [{ draft_revision: 99 }, { schema_version: 'wrong' }, { profile_id: 'other-account' }, { profile_revision: 4 }]) {
    const { client } = seam((path, _, result) => path.endsWith('/prefill') ? Response.json({ ...result, ...patch }) : undefined);
    await assert.rejects(() => client.prefill.load(context, emptyValues(), new AbortController().signal));
  }
  const { client } = seam();
  assert.equal((await client.prefill.load(context, { ...emptyValues(), applicant_full_name: 'FICTIONAL PERSON' }, new AbortController().signal)).rows.length, 1);
});
test('401 and account/session changes expire the boundary; 404/409/503 stay explicit without fallback data', async () => {
  for (const status of [401, 404, 409, 503]) {
    const { client } = seam(path => path === '/api/profile/v2' ? new Response(null, { status }) : undefined);
    await assert.rejects(() => client.get(new AbortController().signal), error => status === 401 ? (error as Error).name === 'SessionExpired' : error instanceof ProfileError && error.status === status);
  }
  let checks = 0;
  const { client } = seam(path => path === '/api/auth/session' && ++checks > 1 ? Response.json({ ...session, user: { ...session.user, id: 'fixture-b' } }) : undefined);
  await assert.rejects(() => client.get(new AbortController().signal), { name: 'SessionExpired' });
});
