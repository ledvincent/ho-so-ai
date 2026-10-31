import { EMPTY_PROFILE, PROFILE_LIMITS, type ProfileFields } from '@/lib/contracts';
import { validateProfile, type FieldId } from '@/lib/forms/draft';

export const CHAT_FIELDS: ReadonlyArray<{ field: FieldId; label: string; prompt: string; placeholder: string }> = [
  { field: 'full_name', label: 'Họ và tên', prompt: 'Bạn muốn điền họ và tên nào? Chỉ nhập một tên giả định.', placeholder: 'Ví dụ: Nguyễn Văn Mẫu' },
  { field: 'date_of_birth', label: 'Ngày sinh', prompt: 'Ngày sinh là ngày nào? Nhập đúng dạng YYYY-MM-DD để tránh nhầm ngày và tháng.', placeholder: 'Ví dụ: 1994-05-16' },
  { field: 'nationality', label: 'Quốc tịch', prompt: 'Bạn muốn điền quốc tịch nào? Nhập đúng nội dung cần ghi.', placeholder: 'Ví dụ: Việt Nam' },
  { field: 'address', label: 'Địa chỉ', prompt: 'Bạn muốn điền địa chỉ nào? Dùng địa chỉ giả định, trên một dòng.', placeholder: 'Ví dụ: 123 đường Mẫu, phường Minh Họa' },
  { field: 'phone_number', label: 'Số điện thoại', prompt: 'Bạn muốn điền số điện thoại nào? Dùng một số giả định.', placeholder: 'Ví dụ: +84 000 000 000' },
  { field: 'email', label: 'Email', prompt: 'Bạn muốn điền email nào? Dùng địa chỉ email mẫu.', placeholder: 'Ví dụ: mau@example.test' },
];

export type DemoAnswer =
  | { kind: 'apply'; field: FieldId; value: string }
  | { kind: 'clarify'; message: string };

/** A literal, single-field adapter. No model call, target inference or value rewriting. */
export function resolveDemoAnswer(target: unknown, answer: string): DemoAnswer {
  if (typeof target !== 'string' || !Object.hasOwn(EMPTY_PROFILE, target)) {
    return { kind: 'clarify', message: 'Hãy chọn một mục trên văn bản hoặc bên dưới rồi nhập giá trị cho mục đó.' };
  }
  const field = target as FieldId;
  if (!answer.trim()) return { kind: 'clarify', message: 'Hãy nhập một giá trị để điền. Nếu muốn xóa, hãy sửa trực tiếp trên văn bản.' };
  if (/[\r\n]/.test(answer)) return { kind: 'clarify', message: 'Hãy gửi một giá trị trên một dòng cho mục đang chọn. Bản minh họa không tách nhiều thông tin hay diễn giải nội dung pháp lý.' };
  if (/[\u0000-\u001F\u007F]/.test(answer)) return { kind: 'clarify', message: 'Hãy nhập văn bản thông thường, không kèm ký tự điều khiển.' };
  // Refuse obvious requests/questions rather than interpreting them as profile values.
  if (/[?？]/.test(answer) || /^(?:hãy|giúp tôi|làm sao|làm thế nào|tôi cần|tôi muốn|cần những|có cần|xin hỏi|what|how|why|which|please|can you)\s/iu.test(answer.trim())
    || /(?:thủ tục|nộp hồ sơ|điều kiện pháp lý|tư vấn pháp lý|legal advice)/iu.test(answer)) {
    return { kind: 'clarify', message: 'Bản minh họa chỉ điền giá trị bạn nhập vào mục đã chọn; không trả lời câu hỏi hay tư vấn thủ tục. Hãy gửi đúng một giá trị cần ghi.' };
  }
  if (field === 'date_of_birth' && !/^\d{4}-\d{2}-\d{2}$/.test(answer)) {
    return { kind: 'clarify', message: 'Hãy nhập ngày sinh theo dạng YYYY-MM-DD, ví dụ 1994-05-16. Không tự suy đoán ngày và tháng từ cách viết khác.' };
  }
  const candidate: ProfileFields = { ...EMPTY_PROFILE, [field]: answer };
  const error = validateProfile(candidate)[field];
  if (error) {
    const message = error.startsWith('Use ') && error.endsWith(' characters or fewer.')
      ? `Mục này nhận tối đa ${PROFILE_LIMITS[field]} ký tự. Hãy rút gọn rồi gửi lại.`
      : field === 'date_of_birth' ? 'Ngày này không hợp lệ. Hãy kiểm tra ngày sinh và dùng dạng YYYY-MM-DD.'
        : field === 'email' ? 'Email chưa đúng định dạng. Hãy nhập đầy đủ, ví dụ mau@example.test.'
          : 'Giá trị này chưa hợp lệ. Hãy kiểm tra mục đang chọn rồi gửi lại.';
    return { kind: 'clarify', message };
  }
  return { kind: 'apply', field, value: answer };
}

/** Choose the next empty field in display order without supplying any value. */
export function nextChatField(values: ProfileFields, applied: FieldId): FieldId {
  const index = CHAT_FIELDS.findIndex((item) => item.field === applied);
  const following = [...CHAT_FIELDS.slice(index + 1), ...CHAT_FIELDS.slice(0, index)];
  return (following.find((item) => !values[item.field]?.trim()) ?? following[0] ?? CHAT_FIELDS[0]).field;
}
