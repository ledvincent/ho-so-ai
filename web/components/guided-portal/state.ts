import { editableFields, emptyValues, fieldIssue, payloadValues, schema, type Values, type WorkflowSchema } from '@/components/na5-demo/model';

export type Message = { role: 'user' | 'assistant'; content: string; ui?: boolean };
export type Change = { id: string; before: string; after: string };
export function appendUserTurn<T extends Message>(messages: readonly T[], content: string): (T | Message)[] {
  return [...messages, { role: 'user', content }];
}
/** UI view model only. AUTH-02/CHAT-01 owns the eventual HTTP contract. */
export type GuidedReply = { values: Values; answer: string; nextField: string | null; ui?: boolean };
export type GuidedAdapter = (input: { message: string; values: Values; revision: number; focusField: string | null; history: Message[]; signal: AbortSignal }) => Promise<GuidedReply>;

export function nextMissing(values: Values, source: WorkflowSchema = schema) {
  return editableFields(values, source).find(field => field.required && fieldIssue(field, values[field.id] ?? '')) ?? null;
}
export function changesBetween(before: Values, after: Values): Change[] {
  return [...new Set([...Object.keys(before), ...Object.keys(after)])]
    .filter(id => (before[id] ?? '') !== (after[id] ?? ''))
    .map(id => ({ id, before: before[id] ?? '', after: after[id] ?? '' }));
}
export function checkedValues(raw: Values, source: WorkflowSchema = schema): Values {
  if (!raw || typeof raw !== 'object' || Object.values(raw).some(value => typeof value !== 'string')) throw new Error('Invalid draft response');
  if (Object.entries(source.fixed_values).some(([id, value]) => raw[id] !== value)) throw new Error('Invalid workflow response');
  const normalized = payloadValues(raw, source);
  for (const field of editableFields(normalized, source)) {
    const value = normalized[field.id];
    if (value && fieldIssue(field, value)) throw new Error('Invalid field response');
  }
  return normalized;
}
export const fieldLabel = (id: string, source: WorkflowSchema = schema) => source.fields.find(field => field.id === id)?.label ?? id;
export const initialDraft = emptyValues;
