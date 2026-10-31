import { sameSession, sessionRequest, SessionExpired, ServiceUnavailable, type LocalSession } from '@/components/guided-portal/api';
import { schema } from '@/components/na5-demo/model';
import type { Candidate, DiscoveryAdapter, FormReference, ProcedureAnswer } from './model';
import { readRequirements } from './dossier-model';

const codePattern = /^\d\.\d{6}$/;
const hashPattern = /^[a-f0-9]{64}$/;
const invalid = () => new ServiceUnavailable();
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
  return { status: data.status, answer: data.answer, citations, model: data.model };
}
const canonical = (value: any): string => JSON.stringify(value && typeof value === 'object' ? Array.isArray(value) ? value.map(item => JSON.parse(canonical(item))) : Object.fromEntries(Object.keys(value).sort().map(key => [key, JSON.parse(canonical(value[key]))])) : value);

/** Exact DISCOVERY-01 browser routes; session credentials never leave the BFF. */
export function createDiscoveryAdapter(identity: LocalSession, fetcher: typeof fetch = fetch): DiscoveryAdapter {
  async function request(path: string, signal: AbortSignal, body?: unknown) {
    if (!sameSession(identity, await sessionRequest(signal, fetcher))) throw new SessionExpired();
    const response = await fetcher(path, { method: body ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store', signal, ...(body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}) });
    if (response.status === 401) throw new SessionExpired();
    if (!response.ok) throw invalid();
    const data = await response.json();
    if (!sameSession(identity, await sessionRequest(signal, fetcher))) throw new SessionExpired();
    return data;
  }
  return {
    async chat(message, history, procedureCode, signal) {
      if (message.trim().length < 2 || message.trim().length > 1000) throw invalid();
      return readAnswer(await request('/api/discovery/chat', signal, { message: message.trim(), history: history.filter(item => item.content.trim().length > 0 && item.content.trim().length <= 8000).slice(-12), ...(procedureCode ? { procedure_code: procedureCode } : {}) }));
    },
    async search(query, signal) {
      if (query.trim().length < 2 || query.trim().length > 1000) throw invalid();
      return readSearch(await request('/api/discovery/search', signal, { query: query.trim() }));
    },
    async detail(candidate, signal) {
      if (!codePattern.test(candidate.code)) throw invalid();
      const data = object(await request(`/api/discovery/procedures/${candidate.code}`, signal));
      if (data.code !== candidate.code || data.name !== candidate.name || !Array.isArray(data.forms)) throw invalid();
      const provenance = [`Danh mục Vincent · ${data.code}`];
      if (safeSourceUrl(data.source_url)) provenance.push(`Nguồn: ${data.source_url}`);
      if (typeof data.sha256 === 'string' && hashPattern.test(data.sha256)) provenance.push(`Bản chụp nguồn: ${data.sha256}`);
      if (typeof data.fetched_at === 'string') provenance.push(`Thời điểm lấy nguồn: ${data.fetched_at}`);
      const factsReady = data.analysis?.facts_ready === true;
      provenance.push(factsReady ? 'Dữ liệu thủ tục có thể được kiểm tra tiếp. Mẫu vẫn giữ trạng thái duyệt riêng.' : 'Dữ liệu phân tích chưa sẵn sàng; chỉ xem tài liệu gốc.');
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
      return { candidate, forms, provenance, fixture: false, factsReady, requirements: readRequirements(data.requirements, formIds), sourceVersion: typeof data.sha256 === 'string' ? data.sha256 : undefined, sourceUrl: safeSourceUrl(data.source_url) ? data.source_url : undefined, fetchedAt: typeof data.fetched_at === 'string' ? data.fetched_at : undefined, otherForms };
    },
    async verifyWorkflow(candidate, formSha, signal) {
      if (!codePattern.test(candidate.code) || !hashPattern.test(formSha)) throw invalid();
      const data = object(await request(`/api/discovery/procedures/${candidate.code}/forms/${formSha}/schema`, signal));
      if (data.procedure_code !== schema.procedure_code || data.review_status !== schema.review_status || data.revision !== schema.revision || data.effective_from !== schema.effective_from || canonical(data.fields) !== canonical(schema.fields) || canonical(data.fixed_values) !== canonical(schema.fixed_values)) throw invalid();
    },
  };
}
