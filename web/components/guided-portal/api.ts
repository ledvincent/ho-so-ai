import { schema, updateValue, type Values } from '@/components/na5-demo/model';
import { checkedValues, type GuidedAdapter } from './state';

export type LocalSession = { user: { id: string; username: string; identity_provider: 'local' }; expires_at: number };
export class SessionExpired extends Error { constructor() { super('Session expired'); this.name = 'SessionExpired'; } }
export class ServiceUnavailable extends Error { constructor() { super('Service unavailable'); this.name = 'ServiceUnavailable'; } }
type Fetcher = typeof fetch;
export function parseSession(raw: unknown): LocalSession {
  const value = raw as LocalSession;
  if (!value?.user || typeof value.user.id !== 'string' || !value.user.id || typeof value.user.username !== 'string' || value.user.identity_provider !== 'local' || !Number.isFinite(value.expires_at) || value.expires_at <= 0) throw new ServiceUnavailable();
  return value;
}
export const sameSession = (left: LocalSession, right: LocalSession) => left.user.id === right.user.id && left.expires_at === right.expires_at;
export async function sessionRequest(signal?: AbortSignal, fetcher: Fetcher = fetch): Promise<LocalSession> {
  const response = await fetcher('/api/auth/session', { credentials: 'same-origin', cache: 'no-store', signal });
  if (response.status === 401) throw new SessionExpired();
  if (!response.ok) throw new ServiceUnavailable();
  return parseSession(await response.json());
}
export async function loginRequest(username: string, password: string, signal: AbortSignal, fetcher: Fetcher = fetch) {
  const response = await fetcher('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', cache: 'no-store', body: JSON.stringify({ username, password }), signal });
  if (!response.ok) throw new ServiceUnavailable();
  return parseSession(await response.json());
}
export async function logoutRequest(fetcher: Fetcher = fetch) {
  const response = await fetcher('/api/auth/logout', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin', cache: 'no-store', body: '{}' });
  if (!response.ok) throw new ServiceUnavailable();
  const result = await response.json(); if (result?.ok !== true) throw new ServiceUnavailable();
}
export async function verifySchema(signal?: AbortSignal, fetcher: Fetcher = fetch) {
  const response = await fetcher('/api/chat/schema', { credentials: 'same-origin', cache: 'no-store', signal });
  if (response.status === 401) throw new SessionExpired();
  if (!response.ok) throw new ServiceUnavailable();
  const data = await response.json();
  if (data.procedure_code !== '1.001146' || data.schema_version !== '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3' || data.review_status !== 'draft' || data.fields?.length !== 43 || data.fixed_values?.request_type !== 'stay_extension') throw new ServiceUnavailable();
}
export function createGuidedAdapter(identity: LocalSession, fetcher: Fetcher = fetch): GuidedAdapter {
  return async input => {
    const before = await sessionRequest(input.signal, fetcher);
    if (!sameSession(identity, before)) throw new SessionExpired();
    const requestId = crypto.randomUUID();
    const response = await fetcher('/api/chat/assist', { method: 'POST', credentials: 'same-origin', cache: 'no-store', headers: { 'Content-Type': 'application/json' }, signal: input.signal, body: JSON.stringify({ request_id: requestId, draft_revision: input.revision, procedure_code: '1.001146', intent: 'form_answer', message: input.message, focus_field: input.focusField, values: input.values }) });
    if (response.status === 401) throw new SessionExpired();
    if (!response.ok) throw new ServiceUnavailable();
    const result = await response.json();
    if (result.request_id !== requestId || result.draft_revision !== input.revision || result.procedure_code !== '1.001146' || result.schema_version !== '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3' || result.review_status !== 'draft' || !['proposed', 'needs_clarification', 'question', 'complete'].includes(result.status) || typeof result.assistant_text !== 'string' || !Array.isArray(result.proposed_changes)) throw new ServiceUnavailable();
    if (['needs_clarification', 'question'].includes(result.status) && result.proposed_changes.length) throw new ServiceUnavailable();
    let next: Values = { ...input.values };
    const seen = new Set<string>();
    const changes = [...result.proposed_changes].sort((a, b) => (a.field_id === 'host_type' ? -2 : a.field_id === 'sponsor_kind' ? -1 : 0) - (b.field_id === 'host_type' ? -2 : b.field_id === 'sponsor_kind' ? -1 : 0));
    for (const change of changes) {
      if (typeof change.field_id !== 'string' || typeof change.value !== 'string' || seen.has(change.field_id)) throw new ServiceUnavailable();
      seen.add(change.field_id); next = updateValue(next, change.field_id, change.value);
    }
    if (result.next_field !== null && !schema.fields.some(field => field.id === result.next_field)) throw new ServiceUnavailable();
    const after = await sessionRequest(input.signal, fetcher);
    if (!sameSession(identity, after)) throw new SessionExpired();
    return { values: checkedValues(next), answer: result.assistant_text, nextField: result.next_field };
  };
}
