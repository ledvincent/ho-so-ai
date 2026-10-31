import { sameSession, sessionRequest, SessionExpired, ServiceUnavailable, type LocalSession } from '@/components/guided-portal/api';
import { schema, payloadValues } from '@/components/na5-demo/model';
import { checkedValues } from '@/components/guided-portal/state';
import type { Candidate, DiscoveryAdapter, FormReference, ProcedureAnswer } from './model';
import { readRequirements } from './dossier-model';
import { readDocumentCards, readFormAction } from './document-model';
import { readDocumentPages, readDocumentSchema } from './document-schema';

const codePattern = /^\d\.\d{6}$/;
const hashPattern = /^[a-f0-9]{64}$/;
const invalid = () => new ServiceUnavailable();
export class DiscoveryRequestError extends ServiceUnavailable { constructor(public status: number) { super(); this.name = 'DiscoveryRequestError'; } }
function object(value: unknown): Record<string, any> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw invalid();
  return value as Record<string, any>;
}
export function safeSourceUrl(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password; } catch { return false; }
}
export function readSearch(raw: unknown) {
  const data = object(raw);
  if (!['found', 'not_found'].includes(data.status) || !Array.isArray(data.results) || data.results.length > 5) throw invalid();
  const seen = new Set<string>();
  const candidates: Candidate[] = data.results.map((rawItem: unknown) => {
    const item = object(rawItem);
    if (typeof item.code !== 'string' || !codePattern.test(item.code) || typeof item.name !== 'string' || !item.name.trim() || seen.has(item.code)) throw invalid();
    seen.add(item.code); return { code: item.code, name: item.name };
  });
  if ((data.status === 'not_found') !== (candidates.length === 0)) throw invalid();
  return { status: data.status as 'found' | 'not_found', candidates };
}
export function readAnswer(raw: unknown): ProcedureAnswer {
  const data = object(raw);
  if (!['answered', 'needs_clarification', 'insufficient_context', 'out_of_scope'].includes(data.status) || typeof data.answer !== 'string' || data.answer.length > 16000 || !Array.isArray(data.citations) || data.citations.length > 20 || !(data.model === null || typeof data.model === 'string')) throw invalid();
  const seen = new Set<string>();
  const citations = data.citations.map((rawItem: unknown) => {
    const item = object(rawItem);
    if (typeof item.id !== 'string' || !item.id || seen.has(item.id) || typeof item.title !== 'string' || !safeSourceUrl(item.url)) throw invalid();
    seen.add(item.id); return { id: item.id, title: item.title, url: item.url };
  });
  if (data.status === 'answered' && !citations.length) throw invalid();
  const choices = data.choices ?? [];
  const retrievalState = data.retrieval_state ?? null;
  const procedureCode = data.procedure_code ?? null;
  if (!Array.isArray(choices) || choices.length > 20 || !(retrievalState === null || (typeof retrievalState === 'string' && retrievalState.length > 0 && retrievalState.length <= 12000)) || !(procedureCode === null || (typeof procedureCode === 'string' && codePattern.test(procedureCode)))) throw invalid();
  const choiceIds = new Set<string>();
  const checkedChoices = choices.map((rawChoice: unknown) => {
    const choice = object(rawChoice);
    if (typeof choice.id !== 'string' || !choice.id || choice.id.length > 1000 || choiceIds.has(choice.id) || typeof choice.label !== 'string' || !choice.label || choice.label.length > 2000) throw invalid();
    choiceIds.add(choice.id); return { id: choice.id, label: choice.label };
  });
  if (checkedChoices.length && !retrievalState) throw invalid();
  return { status: data.status, answer: data.answer, citations, model: data.model, choices: checkedChoices, retrievalState, procedureCode, documents: readDocumentCards(data.documents ?? [], citations, procedureCode ?? undefined) };
}
const canonical = (value: any): string => JSON.stringify(value && typeof value === 'object' ? Array.isArray(value) ? value.map(item => JSON.parse(canonical(item))) : Object.fromEntries(Object.keys(value).sort().map(key => [key, JSON.parse(canonical(value[key]))])) : value);

/** Exact DISCOVERY-01 browser routes; session credentials never leave the BFF. */
export function createDiscoveryAdapter(identity: LocalSession, fetcher: typeof fetch = fetch): DiscoveryAdapter {
  async function requestResponse(path: string, signal: AbortSignal, body?: unknown) {
    if (!sameSession(identity, await sessionRequest(signal, fetcher))) throw new SessionExpired();
    const response = await fetcher(path, { method: body ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store', signal, ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) });
    if (response.status === 401) throw new SessionExpired();
    if (!sameSession(identity, await sessionRequest(signal, fetcher))) throw new SessionExpired();
    if (!response.ok) throw new DiscoveryRequestError(response.status);
    return response;
  }
  async function request(path: string, signal: AbortSignal, body?: unknown) { return (await requestResponse(path, signal, body)).json(); }
  async function detailCode(code: string, signal: AbortSignal, expectedName?: string) {
      if (!codePattern.test(code)) throw invalid();
      const data = object(await request(`/api/discovery/procedures/${code}`, signal));
      if (data.code !== code || typeof data.name !== 'string' || !data.name || (expectedName !== undefined && data.name !== expectedName) || !Array.isArray(data.forms)) throw invalid();
      const rawSections = data.document_json?.sections;
      const sourceSections = Array.isArray(rawSections) && rawSections.length <= 200 ? rawSections.filter((section: any) => section && typeof section.heading === 'string' && typeof section.text_verbatim === 'string').map((section: any) => ({ heading: section.heading, text: section.text_verbatim })) : undefined;
      const candidate: Candidate = { code, name: data.name, ...(typeof data.name_en === 'string' && data.name_en.trim() ? { nameEn: data.name_en } : {}) };
      const provenance = [`Danh mục Vincent · ${data.code}`];
      if (safeSourceUrl(data.source_url)) provenance.push(`Nguồn: ${data.source_url}`);
      if (typeof data.sha256 === 'string' && hashPattern.test(data.sha256)) provenance.push(`Bản chụp nguồn: ${data.sha256}`);
      if (typeof data.fetched_at === 'string') provenance.push(`Thời điểm lấy nguồn: ${data.fetched_at}`);
      const factsReady = data.analysis?.facts_ready === true;
      provenance.push(factsReady ? 'Dữ liệu thủ tục có thể được kiểm tra tiếp. Mẫu vẫn giữ trạng thái duyệt riêng.' : 'Dữ liệu phân tích còn hạn chế. Nếu có quy trình điền bên dưới, bạn có thể chuẩn bị và xem trước bản nháp. Việc duyệt mẫu và tải xuống được kiểm tra riêng.');
      const forms: FormReference[] = [];
      const formIds: number[] = []; const otherForms: { id: number; label: string }[] = [];
      for (const raw of data.forms) {
        const item = object(raw);
        if (Number.isSafeInteger(item.id) && item.id > 0) formIds.push(item.id);
        if (item.form_sha256 === null) { provenance.push('Có tài liệu chưa tải xuống; chưa thể xác nhận quy trình điền.'); if (Number.isSafeInteger(item.id)) otherForms.push({ id: item.id, label: typeof item.label === 'string' ? item.label : 'Tài liệu nguồn' }); continue; }
        if (typeof item.form_sha256 !== 'string' || !hashPattern.test(item.form_sha256)) throw invalid();
        const href = `/api/discovery/procedures/${candidate.code}/forms/${item.form_sha256}/original`;
        if (item.original_download_url != null && item.original_download_url !== href) throw invalid();
        forms.push({ id: item.id, sha256: item.form_sha256, label: typeof item.label === 'string' ? item.label : 'Tài liệu gốc', reviewStatus: typeof item.review_status === 'string' ? item.review_status : undefined, revision: typeof item.revision_reference === 'string' ? item.revision_reference : undefined, ...(item.original_download_url ? { href } : {}) });
        if (typeof item.revision_reference === 'string') provenance.push(`Phiên bản: ${item.revision_reference}`);
        if (typeof item.review_status === 'string') provenance.push(`Trạng thái mẫu: ${item.review_status}`);
      }
      return { candidate, forms, provenance, fixture: false, factsReady, requirements: readRequirements(data.requirements, formIds), sourceVersion: typeof data.sha256 === 'string' ? data.sha256 : undefined, sourceUrl: safeSourceUrl(data.source_url) ? data.source_url : undefined, fetchedAt: typeof data.fetched_at === 'string' ? data.fetched_at : undefined, otherForms, sourceSections };
  }
  return {
    async chat(message, history, procedureCode, signal, turn) {
      if (message.trim().length < 2 || message.trim().length > 1000) throw invalid();
      const state = turn?.retrievalState;
      const choice = turn?.clarificationAnswer;
      if ((state != null && (typeof state !== 'string' || !state || state.length > 12000)) || (choice != null && (!state || !choice || choice.length > 1000))) throw invalid();
      return readAnswer(await request('/api/discovery/chat', signal, { message: message.trim(), history: history.filter(item => item.content.trim().length > 0 && item.content.trim().length <= 16000).slice(-12), ...(!choice && procedureCode ? { procedure_code: procedureCode } : {}), ...(state !== undefined ? { retrieval_state: state } : {}), ...(choice ? { clarification_answer: choice } : {}) }));
    },
    async search(query, signal) {
      if (query.trim().length < 2 || query.trim().length > 1000) throw invalid();
      return readSearch(await request('/api/discovery/search', signal, { query: query.trim() }));
    },
    async detail(candidate, signal) { const detail = await detailCode(candidate.code, signal, candidate.name); return { ...detail, candidate: { ...detail.candidate, ...(candidate.nameEn ? { nameEn: candidate.nameEn } : {}) } }; },
    detailCode,
    async setup(signal) {
      const data = object(await request('/api/discovery/setup', signal));
      if (typeof data.generation_configured !== 'boolean' || typeof data.index_ready !== 'boolean' || !Array.isArray(data.procedures) || data.procedures.length > 500) throw invalid();
      const seen = new Set<string>();
      const procedures = data.procedures.map((raw: unknown) => { const item = object(raw); if (typeof item.code !== 'string' || !codePattern.test(item.code) || seen.has(item.code) || typeof item.name !== 'string' || !item.name || !(item.name_en == null || typeof item.name_en === 'string')) throw invalid(); seen.add(item.code); return { code: item.code, name: item.name, ...(item.name_en ? { nameEn: item.name_en } : {}) }; });
      return { configured: data.generation_configured, indexReady: data.index_ready, procedures };
    },
    async documents(code, signal) {
      if (!codePattern.test(code)) throw invalid();
      const data = object(await request(`/api/discovery/procedures/${code}/documents`, signal));
      if (!Array.isArray(data.documents) || data.documents.length > 100) throw invalid();
      const result = data.documents.map((raw: unknown) => readFormAction(raw, code));
      if (new Set(result.map(item => item.document_id)).size !== result.length) throw invalid();
      return result;
    },
    async document(action, signal) {
      const checked = readFormAction(action, action.procedure_code);
      const workflow = readDocumentSchema(await request(checked.schema_url, signal), checked);
      const pages = readDocumentPages(await request(checked.template_pages_url, signal), workflow);
      return { action: checked, schema: workflow, pages };
    },
    async validateDocument(workflow, values, signal) {
      const action = readFormAction(workflow.action, workflow.schema.procedure_code);
      const normalized = payloadValues(values, workflow.schema);
      const data = object(await request(action.validate_url, signal, { values: normalized, template_version: action.template_version }));
      if (data.template_version !== action.template_version || !Array.isArray(data.missing_fields) || data.missing_fields.length > workflow.schema.fields.length || typeof data.ready_for_preview !== 'boolean' || typeof data.note !== 'string') throw invalid();
      const checked = checkedValues(object(data.values), workflow.schema);
      if (canonical(checked) !== canonical(normalized)) throw invalid();
      const seen = new Set<string>();
      const missing = data.missing_fields.map((raw: unknown) => { const item = object(raw); const field = workflow.schema.fields.find(field => field.id === item.id); if (!field || field.label !== item.label || seen.has(field.id)) throw invalid(); seen.add(field.id); return { id: field.id, label: field.label }; });
      if (data.ready_for_preview !== (missing.length === 0)) throw invalid();
      return { values: checked, missing, ready: data.ready_for_preview, note: data.note };
    },
    async previewDocument(workflow, values, signal) {
      const action = readFormAction(workflow.action, workflow.schema.procedure_code);
      const response = await requestResponse(action.preview_pages_url, signal, { values: payloadValues(values, workflow.schema), template_version: action.template_version });
      const reviewToken = response.headers.get('X-Review-Token');
      if (!reviewToken || reviewToken.length > 200000 || /[\r\n]/.test(reviewToken)) throw invalid();
      // Download remains locked in this draft UI; do not retain or expose its value-bearing token.
      return readDocumentPages(await response.json(), workflow.schema);
    },
    async verifyWorkflow(candidate, formSha, signal) {
      if (!codePattern.test(candidate.code) || !hashPattern.test(formSha)) throw invalid();
      const data = object(await request(`/api/discovery/procedures/${candidate.code}/forms/${formSha}/schema`, signal));
      if (data.procedure_code !== schema.procedure_code || data.review_status !== schema.review_status || data.revision !== schema.revision || data.effective_from !== schema.effective_from || canonical(data.fields) !== canonical(schema.fields) || canonical(data.fixed_values) !== canonical(schema.fixed_values)) throw invalid();
    },
  };
}
