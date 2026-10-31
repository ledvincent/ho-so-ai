/** Internal UI view models, not an invented Vincent wire response. */
export type Candidate = { code: string; name: string };
export type FormReference = { sha256: string; label: string; href?: string };
export type ProcedureDetail = { candidate: Candidate; forms: FormReference[]; provenance: string[]; fixture: boolean; factsReady: boolean };
export type SearchResult = { status: 'found' | 'not_found'; candidates: Candidate[] };
export type Citation = { id: string; title: string; url: string };
export type ProcedureAnswer = { status: 'answered' | 'needs_clarification' | 'insufficient_context' | 'out_of_scope'; answer: string; citations: Citation[]; model: string | null };
export type HistoryTurn = { role: 'user' | 'assistant'; content: string };
export type DiscoveryAdapter = {
  chat: (message: string, history: HistoryTurn[], procedureCode: string | null, signal: AbortSignal) => Promise<ProcedureAnswer>;
  search: (query: string, signal: AbortSignal) => Promise<SearchResult>;
  detail: (candidate: Candidate, signal: AbortSignal) => Promise<ProcedureDetail>;
  verifyWorkflow: (candidate: Candidate, formSha: string, signal: AbortSignal) => Promise<void>;
};
export const NA5_CODE = '1.001146';
export const NA5_FORM = 'a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751';
export const GREETING = 'Bạn cần hỗ trợ thủ tục gì?';
export function supportedWorkflow(detail: ProcedureDetail, formSha: string | null) {
  return detail.factsReady && detail.candidate.code === NA5_CODE && formSha === NA5_FORM && detail.forms.some(form => form.sha256 === formSha);
}
export function currentCandidate(candidates: Candidate[], candidate: Candidate) {
  return candidates.find(item => item.code === candidate.code && item.name === candidate.name) ?? null;
}
export function acceptsDiscoveryReply(request: number, current: number, signal: AbortSignal) {
  return request === current && !signal.aborted;
}
export const unavailableDiscovery: DiscoveryAdapter = {
  async chat() { throw new Error('DiscoveryUnavailable'); },
  async search() { throw new Error('DiscoveryUnavailable'); },
  async detail() { throw new Error('DiscoveryUnavailable'); },
  async verifyWorkflow() { throw new Error('DiscoveryUnavailable'); },
};
