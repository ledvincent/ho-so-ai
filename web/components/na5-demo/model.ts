import schemaData from '@/public/test-fixtures/na5/schema.json';
import exampleData from '@/public/test-fixtures/na5/example.json';

export type Placement = { page: number; bbox: number[]; component?: string; anchor_id?: string };
export type WorkflowField = { id: string; label: string; type: string; group: string; required: boolean; manual?: boolean; inactive?: boolean; hidden?: boolean; max_length: number; multiline?: boolean; repeat?: boolean; when?: Record<string, string>; options?: string[]; placements: Placement[]; marks?: Record<string, Placement> };
export type WorkflowSchema = { procedure_code: string; name: string; revision: string; effective_from: string; review_status: string; fields: WorkflowField[]; fixed_values: Record<string, string> };
export const schema = schemaData as unknown as WorkflowSchema;
export const PROCEDURE_TITLE = 'Gia hạn tạm trú cho người nước ngoài (cấp tỉnh)';
export const example = exampleData as Record<string, string>;
export type Values = Record<string, string>;
export const emptyValues = (): Values => ({ ...schema.fixed_values });
export function applicable(field: WorkflowField, values: Values) {
  return !field.manual && !field.inactive && Object.entries(field.when ?? {}).every(([id, value]) => values[id] === value);
}
export function activeFields(values: Values) { return schema.fields.filter(field => applicable(field, values)); }
export function editableFields(values: Values) { return activeFields(values).filter(field => !field.hidden && !Object.hasOwn(schema.fixed_values, field.id)); }
export function updateValue(values: Values, id: string, value: string): Values {
  const field = schema.fields.find(item => item.id === id);
  if (!field || !applicable(field, values) || Object.hasOwn(schema.fixed_values, id)) throw new Error('Field is not editable in this workflow.');
  const next = { ...schema.fixed_values, ...values, [id]: id === 'applicant_full_name' ? value.toUpperCase() : value };
  // Changing sponsor branch drops now-inapplicable values; never submit hidden data.
  for (const item of schema.fields) if (!applicable(item, next)) delete next[item.id];
  return next;
}
export function payloadValues(values: Values): Values {
  const known = new Set(schema.fields.map(field => field.id));
  if (Object.keys(values).some(id => !known.has(id))) throw new Error('Unknown form fields');
  for (const [id, value] of Object.entries(schema.fixed_values)) if (Object.hasOwn(values, id) && values[id] !== value) throw new Error('This workflow only supports stay extension');
  return Object.fromEntries(activeFields({ ...schema.fixed_values, ...values }).map(field => {
    const value = (schema.fixed_values[field.id] ?? values[field.id] ?? '').trim();
    return [field.id, field.id === 'applicant_full_name' ? value.toUpperCase() : value];
  }));
}
function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value.slice(0, 4) === '0000') return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.valueOf()) && date.toISOString().slice(0, 10) === value;
}
export function fieldIssue(field: WorkflowField, raw: string): string | undefined {
  const value = raw.trim();
  if (field.required && !value) return `Cần điền: ${field.label}`;
  if (/[\u0000-\u0008\u000B-\u001F]/.test(value)) return 'Nội dung có ký tự điều khiển không được hỗ trợ.';
  if ([...value].length > field.max_length) return `Tối đa ${field.max_length} ký tự theo schema.`;
  if (value && field.type === 'date' && !validDate(value)) return 'Nhập ngày hợp lệ theo YYYY-MM-DD; không đoán ngày/tháng.';
  if (value && field.options && !field.options.includes(value)) return 'Chọn đúng một giá trị trong danh sách.';
  return undefined;
}
export function issues(values: Values): Record<string, string> {
  const result: Record<string, string> = {};
  const normalized = payloadValues(values);
  for (const field of activeFields(normalized)) {
    const issue = fieldIssue(field, normalized[field.id] ?? '');
    if (issue) result[field.id] = issue;
  }
  for (const [earlier, later] of [['birth_date', 'entry_date'], ['entry_date', 'permitted_until'], ['permitted_until', 'extension_until'], ['extension_until', 'passport_expiry']]) {
    if (normalized[earlier] && normalized[later] && !result[earlier] && !result[later] && normalized[earlier] > normalized[later]) result[later] = `${later} phải bằng hoặc sau ${earlier}.`;
  }
  return result;
}
export function resolveLiteral(field: WorkflowField, answer: string): { value: string } | { clarification: string } {
  if (!answer.trim()) return { clarification: 'Nhập một giá trị giả định cho mục đang chọn.' };
  if (/[?？]/.test(answer) || (!field.multiline && /[\r\n]/.test(answer))) return { clarification: 'Chỉ điền một giá trị vào mục đang chọn. Câu hỏi thủ tục dùng tab Hỏi về thủ tục.' };
  const issue = fieldIssue(field, answer);
  return issue ? { clarification: issue } : { value: field.id === 'applicant_full_name' ? answer.trim().toUpperCase() : answer.trim() };
}

export type Review = { revision: number; values: Readonly<Values> };
export function captureReview(values: Values, revision: number): Review { return Object.freeze({ revision, values: Object.freeze(payloadValues(values)) }); }
export function canDownload(reviewStatus: string, review: Review | null, revision: number, token: string | null, confirmed: boolean) {
  return reviewStatus === 'reviewed' && review?.revision === revision && Boolean(token) && confirmed;
}
