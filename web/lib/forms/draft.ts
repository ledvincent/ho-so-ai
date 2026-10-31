import { EMPTY_PROFILE, PROFILE_LIMITS, type FormRenderRequest, type ProfileFields } from '@/lib/contracts';

export const DEMO_TEMPLATE_VERSION = 'synthetic-demo-v1';
export type FieldId = keyof ProfileFields;
export type Draft = {
  values: ProfileFields; revision: number; source: 'manual' | 'account';
  acknowledged: boolean; previewRevision: number | null;
};
export function newDraft(): Draft {
  return { values: { ...EMPTY_PROFILE }, revision: 1, source: 'manual', acknowledged: false, previewRevision: null };
}
export function editDraft(draft: Draft, field: FieldId, value: string): Draft {
  return { ...draft, values: { ...draft.values, [field]: value || null }, revision: draft.revision + 1, acknowledged: false, previewRevision: null };
}
export function prefillDraft(draft: Draft, fields: ProfileFields): Draft {
  const values = Object.fromEntries(Object.keys(EMPTY_PROFILE).map((key) => {
    const value = fields[key as FieldId] ?? null;
    if (value !== null && typeof value !== 'string') throw new TypeError('Invalid profile field type');
    return [key, value];
  })) as ProfileFields;
  return { values, revision: draft.revision + 1, source: 'account', acknowledged: false, previewRevision: null };
}
export function clearDraft(draft: Draft): Draft {
  return { ...newDraft(), revision: draft.revision + 1 };
}
export function validateProfile(values: ProfileFields): Partial<Record<FieldId, string>> {
  const errors: Partial<Record<FieldId, string>> = {};
  for (const [id, max] of Object.entries(PROFILE_LIMITS)) {
    const field = id as keyof typeof PROFILE_LIMITS;
    if ([...(values[field] ?? '')].length > max) errors[field] = `Use ${max} characters or fewer.`;
  }
  const date = values.date_of_birth;
  if (date) {
    const parsed = /^\d{4}-\d{2}-\d{2}$/.test(date) ? new Date(`${date}T00:00:00Z`) : null;
    if (!parsed || Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== date) errors.date_of_birth = 'Use a valid date.';
  }
  if (values.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) errors.email = 'Enter a valid email address.';
  return errors;
}
export function captureRequest(draft: Draft): Readonly<FormRenderRequest> {
  return Object.freeze({ values: Object.freeze({ ...draft.values }), revision: draft.revision, template_version: DEMO_TEMPLATE_VERSION, acknowledged: draft.acknowledged });
}
export function isCurrent(draft: Draft, request: Readonly<FormRenderRequest>): boolean {
  return draft.revision === request.revision && request.template_version === DEMO_TEMPLATE_VERSION;
}
export function canDownload(draft: Draft): boolean {
  return draft.acknowledged && draft.previewRevision === draft.revision && Object.keys(validateProfile(draft.values)).length === 0;
}
