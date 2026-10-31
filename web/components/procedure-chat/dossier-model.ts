import type { SourceRequirement } from './model';

/** These are source rows, not a claim that every row is a required document. */
export function readRequirements(raw: unknown, formIds: number[]): SourceRequirement[] | undefined {
  if (raw === undefined) return undefined;
  if (!Array.isArray(raw) || raw.length > 300) throw new Error('Invalid source requirements');
  const seen = new Set<number>();
  return raw.map(item => {
    if (!item || !Number.isSafeInteger(item.id) || item.id < 1 || seen.has(item.id) || !Number.isSafeInteger(item.position) || item.position < 0 || typeof item.group_heading !== 'string' || typeof item.text_verbatim !== 'string' || !item.text_verbatim || !Array.isArray(item.form_ids)) throw new Error('Invalid source requirements');
    seen.add(item.id);
    for (const count of [item.originals, item.copies]) if (count !== null && (!Number.isSafeInteger(count) || count < 0)) throw new Error('Invalid source counts');
    if (item.form_ids.some((id: unknown) => !Number.isSafeInteger(id) || !formIds.includes(id as number))) throw new Error('Unassociated requirement form');
    return { id: item.id, position: item.position, groupHeading: item.group_heading, text: item.text_verbatim, originals: item.originals, copies: item.copies, formIds: [...item.form_ids] };
  }).sort((a, b) => a.position - b.position);
}
