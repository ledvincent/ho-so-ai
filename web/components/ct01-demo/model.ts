import { EMPTY_PROFILE } from '@/lib/contracts';
import { validateProfile } from '@/lib/forms/draft';

// Document-local test values. This is not a profile or production form contract.
export type Ct01Field = 'full_name' | 'date_of_birth' | 'personal_id';
export type Ct01Values = Record<Ct01Field, string>;
export type Ct01Draft = { values: Ct01Values; revision: number };
export type Ct01Snapshot = { readonly values: Readonly<Ct01Values>; readonly revision: number };
export const CT01_FIELDS: ReadonlyArray<{ id: Ct01Field; label: string; prompt: string; placeholder: string }> = [
  { id: 'full_name', label: 'Họ và tên', prompt: 'Bạn muốn điền họ, chữ đệm và tên khai sinh nào? Chỉ dùng một tên giả định.', placeholder: 'Nguyễn Văn Mẫu' },
  { id: 'date_of_birth', label: 'Ngày sinh', prompt: 'Nhập ngày sinh giả định theo dạng YYYY-MM-DD. Mình sẽ đặt ngày, tháng và năm vào đúng ba ô.', placeholder: '1994-05-16' },
  { id: 'personal_id', label: 'Số định danh', prompt: 'Nhập đúng 12 chữ số giả định. Số 0 ở đầu được giữ nguyên; không kiểm tra danh tính thực.', placeholder: '000000000001' },
];
export const EMPTY_CT01: Ct01Values = { full_name: '', date_of_birth: '', personal_id: '' };
export const SAMPLE_CT01: Ct01Values = { full_name: 'Nguyễn Văn Mẫu', date_of_birth: '1994-05-16', personal_id: '000000000001' };
export function newCt01Draft(): Ct01Draft { return { values: { ...EMPTY_CT01 }, revision: 1 }; }
export function editCt01Draft(draft: Ct01Draft, field: Ct01Field, value: string): Ct01Draft {
  return { values: { ...draft.values, [field]: value }, revision: draft.revision + 1 };
}
export function validateCt01(values: Ct01Values): Partial<Record<Ct01Field, string>> {
  const issues: Partial<Record<Ct01Field, string>> = {};
  for (const field of CT01_FIELDS) {
    const value = values[field.id];
    if (!value.trim()) issues[field.id] = `Chưa điền ${field.label.toLocaleLowerCase('vi')}.`;
    else if (/[\u0000-\u001F\u007F]/.test(value)) issues[field.id] = 'Chỉ nhập một dòng văn bản, không kèm ký tự điều khiển.';
  }
  const profileErrors = validateProfile({ ...EMPTY_PROFILE, full_name: values.full_name || null, date_of_birth: values.date_of_birth || null });
  if (profileErrors.full_name) issues.full_name = 'Tên quá dài. Hãy rút gọn dữ liệu thử nghiệm để vừa vùng điền.';
  if (values.date_of_birth && (!/^\d{4}-\d{2}-\d{2}$/.test(values.date_of_birth) || profileErrors.date_of_birth)) issues.date_of_birth = 'Nhập ngày hợp lệ theo dạng YYYY-MM-DD; không suy đoán ngày và tháng.';
  if (values.personal_id && !/^\d{12}$/.test(values.personal_id)) issues.personal_id = 'Nhập đúng 12 chữ số. Giữ số 0 ở đầu, không thêm dấu cách.';
  return issues;
}
export function resolveCt01Answer(field: Ct01Field | null, answer: string): { kind: 'apply'; field: Ct01Field; value: string } | { kind: 'clarify'; message: string } {
  if (!field) return { kind: 'clarify', message: 'Chọn một mục trên văn bản hoặc trong cuộc trò chuyện trước khi trả lời.' };
  if (/[\r\n?？]/.test(answer) || /(?:thủ tục|nộp hồ sơ|tư vấn pháp lý|^tôi cần\s|^làm sao\s|^hãy\s)/iu.test(answer.trim())) return { kind: 'clarify', message: 'Bản thử nghiệm chỉ điền một giá trị vào mục đã chọn. Hãy nhập đúng giá trị cần ghi; không diễn giải thủ tục hay tự đoán thông tin.' };
  const error = validateCt01({ ...EMPTY_CT01, [field]: answer })[field];
  return error ? { kind: 'clarify', message: error } : { kind: 'apply', field, value: answer };
}
export function captureCt01(draft: Ct01Draft): Ct01Snapshot {
  return Object.freeze({ values: Object.freeze({ ...draft.values }), revision: draft.revision });
}
export function ct01SnapshotIsCurrent(draft: Ct01Draft, snapshot: Ct01Snapshot | null): boolean { return snapshot !== null && snapshot.revision === draft.revision; }
export function ct01DateParts(value: string): [string, string, string] {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return ['', '', ''];
  const [year, month, day] = value.split('-'); return [day, month, year];
}
