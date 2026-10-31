import { payloadValues, schema, type Values } from './model';

// Exact producer wire shapes. This intermediate UI uses fixtures, not HTTP.
export const workflowPath = `/workflows/${schema.procedure_code}`;
export const requests = {
  schema: () => ({ method: 'GET' as const, path: `${workflowPath}/schema` }),
  preview: (values: Values) => ({ method: 'POST' as const, path: `${workflowPath}/preview`, body: { values: payloadValues(values) } }),
  download: (values: Values, review_token: string, confirmed: boolean) => ({ method: 'POST' as const, path: `${workflowPath}/download`, body: { values: payloadValues(values), review_token, confirmed } }),
};
export type Turn = { role: 'user' | 'assistant'; content: string };
export type ChatResponse = { status: 'answered' | 'insufficient_context' | 'needs_clarification' | 'out_of_scope'; answer: string; citations: { id: string; title: string; url: string }[]; model: string | null };
export function assistantRequest(message: string, history: Turn[] = []) {
  return { method: 'POST' as const, path: '/assistant/chat', body: { message, procedure_code: schema.procedure_code, history: history.slice(-12) } };
}
export const mockTransport = {
  schema: () => schema,
  chat: async (_request: ReturnType<typeof assistantRequest>): Promise<ChatResponse> => ({ status: 'insufficient_context', answer: 'Chưa kết nối dịch vụ tra cứu của Vincent cho thủ tục 1.001146. Demo chỉ điền NA5 bằng dữ liệu giả; chưa có câu trả lời có nguồn để đối chiếu.', citations: [], model: null }),
};
// Real preview integration must consume application/pdf + X-Review-Token.
// No mock signed token or fake downloadable PDF is created. Download stays locked.
