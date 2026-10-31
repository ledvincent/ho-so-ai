import pinned from '@/lib/discovery/fixtures/e162-na5-schema.json';
import type { DocumentPresentation } from './document-model';
import { readDocumentSchema } from './document-schema';

export const LEGACY_CHAT_SCHEMA = '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3';
const canonical = (value: unknown): string => JSON.stringify(value && typeof value === 'object' ? Array.isArray(value) ? value.map(item => JSON.parse(canonical(item))) : Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, JSON.parse(canonical(item))])) : value);

/** Narrow, owner-verified bridge; other documents keep their own manual workflow. */
export function supportsNa5Profile(workflow: DocumentPresentation): boolean {
  try {
    const expected = readDocumentSchema(pinned, workflow.action);
    return canonical(workflow.schema) === canonical(expected);
  } catch { return false; }
}
