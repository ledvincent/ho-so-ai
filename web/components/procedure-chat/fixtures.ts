import { NA5_CODE, NA5_FORM, type Candidate, type DiscoveryAdapter } from './model';
import { editableFields, resolveLiteral, updateValue } from '@/components/na5-demo/model';
import { nextMissing, type GuidedAdapter } from '@/components/guided-portal/state';

/** Explicitly selected UI scenarios. No query matching, model or retrieval call. */
export type FixtureScenario = 'ambiguous_visa' | 'stay_extension' | 'no_match' | 'unavailable';
const stay: Candidate = { code: NA5_CODE, name: 'Gia hạn tạm trú cho người nước ngoài (cấp tỉnh)' };
const visa: Candidate = { code: '1.003342', name: 'Cấp thị thực cho người nước ngoài tại Việt Nam (cấp trung ương)' };
export const fixtureCatalog: Candidate[] = [stay, visa];
export const fixtureFormAdapter: GuidedAdapter = async input => {
  const field = editableFields(input.values).find(item => item.id === input.focusField) ?? nextMissing(input.values);
  if (!field) return { values: { ...input.values }, nextField: null, answer: 'Tình huống UI: các mục bắt buộc đã được điền. Mẫu vẫn chờ duyệt.' };
  if (!input.message.trim()) return { values: { ...input.values }, nextField: field.id, answer: `Tình huống UI · Nhập dữ liệu giả cho: ${field.label}.` };
  const parsed = resolveLiteral(field, input.message);
  if ('clarification' in parsed) return { values: { ...input.values }, nextField: field.id, answer: parsed.clarification };
  const values = updateValue(input.values, field.id, parsed.value); const next = nextMissing(values);
  return { values, nextField: next?.id ?? null, answer: `Tình huống UI · Đã cập nhật bản nháp.${next ? ` Mục tiếp theo: ${next.label}.` : ''}` };
};
export function fixtureDiscovery(scenario: FixtureScenario): DiscoveryAdapter {
  return {
    async chat() {
      if (scenario === 'unavailable') throw new Error('DiscoveryUnavailable');
      return { status: 'needs_clarification', answer: 'Tình huống thử UI: hãy kiểm tra các kết quả có cấu trúc trước khi chọn thủ tục. Đây không phải trả lời từ dịch vụ tra cứu.', citations: [], model: null };
    },
    async search() {
      if (scenario === 'unavailable') throw new Error('DiscoveryUnavailable');
      return { status: scenario === 'no_match' ? 'not_found' : 'found', candidates: scenario === 'no_match' ? [] : scenario === 'stay_extension' ? [stay] : [visa, stay] };
    },
    async detail(candidate) {
      return { candidate, forms: candidate.code === NA5_CODE ? [{ id: 101, sha256: NA5_FORM, label: 'NA5 · tham chiếu mẫu đã nhận', reviewStatus: 'draft' }, { id: 102, sha256: 'c'.repeat(64), label: 'Tài liệu phụ · giả lập UI', reviewStatus: 'unknown' }] : [], provenance: ['Tình huống kiểm thử giao diện được chọn thủ công. Không phải kết quả tra cứu Vincent hoặc nguồn pháp lý.'], fixture: true, factsReady: true, sourceVersion: 'Tình huống UI; không phải bản nguồn pháp lý', requirements: candidate.code === NA5_CODE ? [{ id: 201, position: 0, groupHeading: 'Ví dụ giả lập, không phải yêu cầu pháp lý', text: 'Tình huống UI: kiểm tra điều kiện A hoặc điều kiện B trước khi chọn tài liệu. Chưa xác định điều kiện áp dụng.', originals: null, copies: null, formIds: [101, 102] }] : [] };
    },
    async verifyWorkflow(candidate, formSha) {
      if (candidate.code !== NA5_CODE || formSha !== NA5_FORM) throw new Error('WorkflowUnsupported');
    },
  };
}
