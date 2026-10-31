import type { Placement, WorkflowField } from '@/components/na5-demo/model';
import type { DocumentSchema, FormAction } from './document-model';

function object(value: unknown): Record<string, any> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid document schema');
  return value as Record<string, any>;
}
function placement(raw: unknown, count: number): Placement {
  const p = object(raw);
  if (!Number.isSafeInteger(p.page) || p.page < 1 || p.page > count || !Array.isArray(p.bbox) || p.bbox.length !== 4 || p.bbox.some((n: unknown) => typeof n !== 'number' || !Number.isFinite(n) || n < 0) || p.bbox[2] <= p.bbox[0] || p.bbox[3] <= p.bbox[1]) throw new Error('Invalid document placement');
  return { ...p, page: p.page, bbox: [...p.bbox] };
}
export function readDocumentSchema(raw: unknown, action: FormAction): DocumentSchema {
  const data = object(raw);
  for (const key of ['document_id', 'procedure_code', 'form_id', 'template_sha256', 'template_version', 'revision', 'review_status', 'applicability', 'download_available'] as const) if (data[key] !== action[key]) throw new Error('Document edition changed');
  if (typeof data.name !== 'string' || !(data.effective_from === null || typeof data.effective_from === 'string') || !Number.isSafeInteger(data.page_count) || data.page_count < 1 || data.page_count > 100 || !Array.isArray(data.fields) || !data.fields.length || data.fields.length > 500 || !Array.isArray(data.date_order)) throw new Error('Invalid document schema');
  const ids = new Set<string>();
  const fields: WorkflowField[] = data.fields.map((rawField: unknown) => {
    const f = object(rawField);
    if (typeof f.id !== 'string' || !/^[a-z][a-z0-9_]{0,99}$/.test(f.id) || ids.has(f.id) || typeof f.label !== 'string' || !['text', 'date', 'choice'].includes(f.type) || typeof f.group !== 'string' || typeof f.required !== 'boolean' || !Number.isSafeInteger(f.max_length) || f.max_length < 1 || f.max_length > 20000 || !Array.isArray(f.placements)) throw new Error('Invalid document field');
    for (const key of ['manual', 'inactive', 'hidden', 'uppercase', 'multiline', 'repeat']) if (f[key] != null && typeof f[key] !== 'boolean') throw new Error('Invalid field behavior');
    const when = object(f.when ?? {});
    if (Object.values(when).some(value => typeof value !== 'string') || (f.options != null && (!Array.isArray(f.options) || f.options.some((value: unknown) => typeof value !== 'string')))) throw new Error('Invalid field condition');
    ids.add(f.id);
    return { ...f, id: f.id, label: f.label, type: f.type, group: f.group, required: f.required, max_length: f.max_length, manual: f.manual ?? false, inactive: f.inactive ?? false, hidden: f.hidden ?? false, uppercase: f.uppercase ?? false, multiline: f.multiline ?? false, repeat: f.repeat ?? false, when: { ...when }, ...(f.options ? { options: [...f.options] } : {}), placements: f.placements.map((p: unknown) => placement(p, data.page_count)), ...(f.marks ? { marks: Object.fromEntries(Object.entries(object(f.marks)).map(([key, p]) => [key, placement(p, data.page_count)])) } : {}) };
  });
  const fixed = object(data.fixed_values);
  if (Object.entries(fixed).some(([key, value]) => !ids.has(key) || typeof value !== 'string')) throw new Error('Invalid fixed field');
  for (const field of fields) if (Object.keys(field.when ?? {}).some(key => !ids.has(key))) throw new Error('Unknown condition field');
  if (data.date_order.some((pair: unknown) => !Array.isArray(pair) || pair.length !== 2 || pair.some(key => typeof key !== 'string' || !ids.has(key)))) throw new Error('Invalid date ordering');
  return { document_id: action.document_id, form_id: action.form_id, procedure_code: action.procedure_code, template_sha256: action.template_sha256, template_version: action.template_version, name: data.name, revision: action.revision, review_status: action.review_status, applicability: action.applicability, download_available: action.download_available, effective_from: data.effective_from, page_count: data.page_count, fields, fixed_values: { ...fixed }, date_order: data.date_order.map((pair: string[]) => [...pair]) };
}
export function readDocumentPages(raw: unknown, schema: DocumentSchema) {
  const data = object(raw);
  if (data.template_version !== schema.template_version || !Array.isArray(data.pages) || data.pages.length !== schema.page_count) throw new Error('Document pages changed');
  const seen = new Set<number>();
  return data.pages.map((rawPage: unknown) => {
    const page = object(rawPage);
    if (!Number.isSafeInteger(page.page_number) || page.page_number < 1 || page.page_number > schema.page_count || seen.has(page.page_number) || typeof page.image_data_url !== 'string' || page.image_data_url.length > 20 * 1024 * 1024 || !/^data:image\/png;base64,[A-Za-z0-9+/]+=*$/.test(page.image_data_url)) throw new Error('Invalid document page');
    seen.add(page.page_number); return { pageNumber: page.page_number, imageUrl: page.image_data_url };
  }).sort((a: { pageNumber: number }, b: { pageNumber: number }) => a.pageNumber - b.pageNumber);
}
