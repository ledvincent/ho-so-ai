import { EMPTY_PROFILE_DETAILS, PROFILE_V2_LIMITS, type ProfileDetails } from '@/lib/profile-v2.generated';
import type { ProfileInput } from './sections';

const definitions: ProfileInput[] = [
  { id: 'basics.full_legal_name', section: 'basics', label: 'Họ tên đầy đủ theo giấy tờ', hint: 'Kiểm tra lại cả thông tin đã lưu trước đây; tài khoản không xác minh tên pháp lý.' },
  { id: 'basics.date_of_birth', section: 'basics', label: 'Ngày sinh', kind: 'date' },
  { id: 'basics.sex_as_on_document', section: 'basics', label: 'Giới tính trên giấy tờ', options: [{ value: 'M', label: 'M' }, { value: 'F', label: 'F' }, { value: 'X', label: 'X' }, { value: 'unspecified', label: 'Không ghi rõ' }] },
  { id: 'basics.nationality_at_birth', section: 'basics', label: 'Quốc tịch khi sinh' },
  { id: 'basics.current_nationality', section: 'basics', label: 'Quốc tịch hiện nay' },
  { id: 'basics.occupation', section: 'basics', label: 'Nghề nghiệp' },
  { id: 'contact.phone_number', section: 'contact', label: 'Số điện thoại', kind: 'tel' },
  { id: 'contact.email', section: 'contact', label: 'Email', hint: 'Hồ sơ có thể giữ giá trị dạng văn bản đã lưu trước đây; kiểm tra trước khi dùng lại.' },
  { id: 'passport.document_number', section: 'passport', label: 'Số hộ chiếu / giấy tờ đi lại', hint: 'Giữ nguyên các số 0 ở đầu.' },
  { id: 'passport.document_type', section: 'passport', label: 'Loại giấy tờ' },
  { id: 'passport.issue_date', section: 'passport', label: 'Ngày cấp', kind: 'date' },
  { id: 'passport.expiry_date', section: 'passport', label: 'Ngày hết hạn', kind: 'date' },
  { id: 'passport.issuing_authority', section: 'passport', label: 'Cơ quan cấp' },
  { id: 'residence.temporary_address_in_vietnam', section: 'residence', label: 'Địa chỉ tạm trú tại Việt Nam', multiline: true },
  { id: 'residence.permanent_address', section: 'residence', label: 'Địa chỉ thường trú', multiline: true },
];
export const profileFields = definitions.map(field => ({ ...field, maxLength: PROFILE_V2_LIMITS[field.id as keyof typeof PROFILE_V2_LIMITS] }));

export const sourceLabel = (path: string) => profileFields.find(field => field.id === path)?.label ?? ({ 'legacy.nationality': 'Quốc tịch đã lưu trước đây', 'legacy.address': 'Địa chỉ đã lưu trước đây' }[path] ?? path);
export function flattenDetails(details: ProfileDetails): Record<string, string | null> {
  return Object.fromEntries(Object.entries(details).flatMap(([group, values]) => Object.entries(values).map(([key, value]) => [`${group}.${key}`, value ?? null])));
}
export function groupedDetails(values: Record<string, string | null>): ProfileDetails {
  return Object.fromEntries(Object.entries(EMPTY_PROFILE_DETAILS).map(([group, fields]) => [group, Object.fromEntries(Object.keys(fields).map(key => [key, values[`${group}.${key}`] || null]))])) as ProfileDetails;
}
export const emptyDetails = () => groupedDetails(flattenDetails(EMPTY_PROFILE_DETAILS));
