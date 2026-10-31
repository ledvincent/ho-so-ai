import { editableFields, emptyValues, fieldIssue, payloadValues, schema, type Values } from '@/components/na5-demo/model';

export type Message = { role: 'user' | 'assistant'; content: string; ui?: boolean };
export type Change = { id: string; before: string; after: string };
export function appendUserTurn<T extends Message>(messages: readonly T[], content: string): (T | Message)[] {
  return [...messages, { role: 'user', content }];
}
/** UI view model only. AUTH-02/CHAT-01 owns the eventual HTTP contract. */
export type GuidedReply = { values: Values; answer: string; nextField: string | null; ui?: boolean };
export type GuidedAdapter = (input: { message: string; values: Values; revision: number; focusField: string | null; history: Message[]; signal: AbortSignal }) => Promise<GuidedReply>;

export function nextMissing(values: Values) {
  return editableFields(values).find(field => field.required && fieldIssue(field, values[field.id] ?? '')) ?? null;
}
export function changesBetween(before: Values, after: Values): Change[] {
  return [...new Set([...Object.keys(before), ...Object.keys(after)])]
    .filter(id => (before[id] ?? '') !== (after[id] ?? ''))
    .map(id => ({ id, before: before[id] ?? '', after: after[id] ?? '' }));
}
export function checkedValues(raw: Values): Values {
  if (!raw || typeof raw !== 'object' || Object.values(raw).some(value => typeof value !== 'string')) throw new Error('Invalid draft response');
  if (raw.request_type !== 'stay_extension') throw new Error('Invalid workflow response');
  const normalized = payloadValues(raw);
  for (const field of editableFields(normalized)) {
    const value = normalized[field.id];
    if (value && fieldIssue(field, value)) throw new Error('Invalid field response');
  }
  return normalized;
}
export const fieldLabel = (id: string) => schema.fields.find(field => field.id === id)?.label ?? id;
export const initialDraft = emptyValues;
