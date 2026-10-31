import type { WorkflowSchema } from '@/components/na5-demo/model';
import type { Citation } from './model';

/** Producer e162791 document identities and actions; never inferred from prose. */
export type FormAction = {
  document_id: string; form_id: string; procedure_code: string;
  template_sha256: string; template_version: string; revision: string;
  review_status: string; applicability: string; download_available: boolean;
  schema_url: string; template_url: string; template_pages_url: string;
  validate_url: string; preview_url: string; preview_pages_url: string; download_url: string;
};
export type DocumentCard = {
  id: string; title: string; kind: 'fillable_form' | 'supporting_document' | 'submission_instruction';
  requirement: 'required' | 'conditional' | 'unconfirmed'; condition: string | null; description: string;
  originals: number | null; copies: number | null; source_ids: string[]; evidence_status: string; form: FormAction | null;
};
export type DocumentSchema = WorkflowSchema & {
  document_id: string; form_id: string; template_sha256: string; template_version: string;
  page_count: number; applicability: string; download_available: boolean; date_order: string[][];
};
export type DocumentPresentation = { action: FormAction; schema: DocumentSchema; pages: { pageNumber: number; imageUrl: string }[] };
export type Clarification = { id: string; label: string };
export type RetrievalTurn = { retrievalState: string | null; clarificationAnswer?: string | null };
export type DocumentEvidence = { documents: DocumentCard[]; citations: Citation[] };

const object = (value: unknown): Record<string, any> => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid document response');
  return value as Record<string, any>;
};
const text = (value: unknown, limit = 2000): value is string => typeof value === 'string' && value.length > 0 && value.length <= limit;
const hash = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const code = (value: unknown): value is string => typeof value === 'string' && /^\d\.\d{6}$/.test(value);
const actions = { schema_url: 'schema', template_url: 'template', template_pages_url: 'template-pages', validate_url: 'validate', preview_url: 'preview', preview_pages_url: 'preview-pages', download_url: 'download' } as const;

export function readFormAction(raw: unknown, expectedCode?: string): FormAction {
  const data = object(raw);
  if (!text(data.document_id, 100) || !/^[a-z0-9][a-z0-9_-]*$/.test(data.document_id) || !text(data.form_id, 100) || !code(data.procedure_code) || (expectedCode && data.procedure_code !== expectedCode) || !hash(data.template_sha256) || !hash(data.template_version) || !text(data.revision, 500) || !text(data.review_status, 100) || !text(data.applicability, 100) || typeof data.download_available !== 'boolean') throw new Error('Invalid document action');
  const result = { document_id: data.document_id, form_id: data.form_id, procedure_code: data.procedure_code, template_sha256: data.template_sha256, template_version: data.template_version, revision: data.revision, review_status: data.review_status, applicability: data.applicability, download_available: data.download_available } as FormAction;
  for (const [key, suffix] of Object.entries(actions)) {
    const producerPath = `/documents/${data.document_id}/${suffix}`;
    const browserPath = `/api/discovery${producerPath}`;
    if (data[key] !== producerPath && data[key] !== browserPath) throw new Error('Unassociated document URL');
    // The authenticated BFF is the only browser destination, never the producer origin.
    result[key as keyof typeof actions] = browserPath;
  }
  return result;
}
export function readDocumentCards(raw: unknown, citations: Citation[], expectedCode?: string): DocumentCard[] {
  if (!Array.isArray(raw) || raw.length > 100) throw new Error('Invalid document cards');
  const ids = new Set<string>(); const sources = new Set(citations.map(item => item.id));
  return raw.map(value => {
    const item = object(value);
    if (!text(item.id, 200) || ids.has(item.id) || !text(item.title, 2000) || !['fillable_form', 'supporting_document', 'submission_instruction'].includes(item.kind) || !['required', 'conditional', 'unconfirmed'].includes(item.requirement) || !(item.condition == null || text(item.condition, 8000)) || typeof (item.description ?? '') !== 'string' || (item.description ?? '').length > 16000 || !text(item.evidence_status, 100) || !Array.isArray(item.source_ids) || item.source_ids.some((id: unknown) => typeof id !== 'string' || !sources.has(id))) throw new Error('Invalid document evidence');
    for (const count of [item.originals, item.copies]) if (count != null && (!Number.isSafeInteger(count) || count < 0)) throw new Error('Invalid document quantity');
    ids.add(item.id);
    const form = item.form == null ? null : readFormAction(item.form, expectedCode);
    if (form && item.kind !== 'fillable_form') throw new Error('Unexpected document workflow');
    return { id: item.id, title: item.title, kind: item.kind, requirement: item.requirement, condition: item.condition ?? null, description: item.description ?? '', originals: item.originals ?? null, copies: item.copies ?? null, source_ids: [...item.source_ids], evidence_status: item.evidence_status, form };
  });
}
export function sameDocument(left: FormAction, right: FormAction) {
  return left.document_id === right.document_id && left.procedure_code === right.procedure_code && left.template_sha256 === right.template_sha256 && left.template_version === right.template_version;
}
