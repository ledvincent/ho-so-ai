import { editableFields, fieldIssue, updateValue, schema as defaultSchema, type Values, type WorkflowSchema } from '@/components/na5-demo/model';

/** UI-only proposal model. No HTTP route/DTO or profile storage is defined here. */
export type PrefillBinding = { session: string; document: string; draftRevision: number; profileId: string; profileRevision: number };
export type PrefillContext = Omit<PrefillBinding, 'profileId' | 'profileRevision'> & { procedureCode: string; formSha: string; schemaVersion: string };
export type PrefillRow = { id: string; target: string; sourceLabel: string; sourceValue: string; value: string; requiresDocument: boolean; selected: boolean; locked?: boolean; issue?: string };
export type PrefillSource = { profileId: string; revision: number; rows: Omit<PrefillRow, 'selected' | 'locked' | 'issue'>[]; warnings: string[] };
export type PrefillClient = {
  load: (context: PrefillContext, draft: Values, signal: AbortSignal) => Promise<PrefillSource>;
  check: (signal: AbortSignal) => Promise<{ profileId: string; profileRevision: number }>;
};
const allowed = new Set(['applicant_full_name', 'birth_date', 'sex', 'birth_nationality', 'current_nationality', 'occupation', 'passport_number', 'passport_type', 'passport_issuer', 'passport_expiry', 'residential_address', 'contact']);
export function proposalIssue(target: string, value: string, draft: Values, workflow: WorkflowSchema = defaultSchema) {
  const field = editableFields(draft, workflow).find(item => item.id === target);
  if (!field || !allowed.has(target)) return 'Mục này không được sao chép từ hồ sơ.';
  return fieldIssue(field, value);
}
export function prepareRows(source: PrefillSource, draft: Values, workflow: WorkflowSchema = defaultSchema): PrefillRow[] {
  const seen = new Set<string>(); const targets = new Set<string>();
  return source.rows.map(row => {
    if (!allowed.has(row.target) || seen.has(row.id) || (targets.has(row.target) && row.target !== 'contact')) throw new Error('Invalid profile proposal');
    const first = !targets.has(row.target); seen.add(row.id); targets.add(row.target);
    const locked = Boolean(draft[row.target]?.trim());
    const value = row.target === 'applicant_full_name' ? row.value.toUpperCase() : row.value;
    const issue = proposalIssue(row.target, value, draft, workflow);
    return { ...row, value, selected: first && !row.requiresDocument && !locked && !issue && Boolean(value.trim()), locked, issue };
  });
}
export function samePrefillBinding(left: PrefillBinding, right: PrefillBinding) {
  return left.session === right.session && left.document === right.document && left.draftRevision === right.draftRevision && left.profileId === right.profileId && left.profileRevision === right.profileRevision;
}
export function selectRow(rows: PrefillRow[], id: string, selected: boolean): PrefillRow[] {
  const target = rows.find(row => row.id === id)?.target;
  return rows.map(row => row.id === id ? { ...row, selected: selected && !row.locked } : selected && row.target === target ? { ...row, selected: false } : row);
}
export function applyRows(rows: PrefillRow[], draft: Values, captured: PrefillBinding, current: PrefillBinding, documentConfirmed = false, workflow: WorkflowSchema = defaultSchema): Values {
  if (!samePrefillBinding(captured, current)) throw new Error('Stale profile proposal');
  let next = { ...draft }; const targets = new Set<string>();
  for (const row of rows.filter(item => item.selected)) {
    if (targets.has(row.target) || (row.requiresDocument && !documentConfirmed) || next[row.target]?.trim() || row.locked || proposalIssue(row.target, row.value, next, workflow)) throw new Error('Draft changed or proposal invalid');
    targets.add(row.target);
    next = updateValue(next, row.target, row.value.trim(), workflow);
  }
  return next;
}
