import english from './locale-en.json';
export type Locale = 'vi' | 'en';
export const LOCALE_KEY = 'hoso-ui-locale';
export const validLocale = (value: unknown): Locale => value === 'en' ? 'en' : 'vi';
const viFields: Record<string, string> = {
  'Full name (capital letters)': 'Họ tên đầy đủ (chữ in hoa)', 'Sex': 'Giới tính', 'Date of birth': 'Ngày sinh', 'Nationality at birth': 'Quốc tịch khi sinh', 'Current nationality': 'Quốc tịch hiện nay', 'Occupation / position': 'Nghề nghiệp / chức vụ',
  'Passport / international travel document number': 'Số hộ chiếu / giấy tờ đi lại quốc tế', 'Passport type / international travel document name': 'Loại hộ chiếu / tên giấy tờ đi lại quốc tế', 'Travel document issuing authority': 'Cơ quan cấp giấy tờ đi lại', 'Travel document expiry date': 'Ngày hết hạn giấy tờ đi lại', 'Most recent entry date': 'Ngày nhập cảnh gần nhất', 'Entry border gate / port': 'Cửa khẩu nhập cảnh', 'Purpose of entry': 'Mục đích nhập cảnh', 'Currently permitted to stay until': 'Được phép tạm trú đến ngày', 'Temporary residential address in Vietnam': 'Địa chỉ tạm trú tại Việt Nam', 'Applicant telephone / email': 'Điện thoại / email của người đề nghị',
  'Who sponsors this application?': 'Ai bảo lãnh cho đề nghị này?', 'Hosting organisation name': 'Tên cơ quan / tổ chức bảo lãnh', 'Hosting organisation address': 'Địa chỉ cơ quan / tổ chức bảo lãnh', 'Hosting organisation telephone / email': 'Điện thoại / email cơ quan bảo lãnh', 'Family sponsor status': 'Tư cách người thân bảo lãnh', 'Family sponsor full name': 'Họ tên người thân bảo lãnh', 'Family sponsor date of birth': 'Ngày sinh người bảo lãnh', 'Sponsor citizen identity card / identity card / passport number': 'Số căn cước / chứng minh nhân dân / hộ chiếu của người bảo lãnh', 'Sponsor identity document issue date': 'Ngày cấp giấy tờ của người bảo lãnh', 'Sponsor identity document issuing authority': 'Cơ quan cấp giấy tờ của người bảo lãnh', 'Sponsor permanent / temporary residence card number': 'Số thẻ thường trú / tạm trú của người bảo lãnh', 'Sponsor residence card issue date': 'Ngày cấp thẻ cư trú của người bảo lãnh', 'Sponsor residence card issuing authority': 'Cơ quan cấp thẻ cư trú của người bảo lãnh', "Family sponsor's relationship to the applicant": 'Quan hệ với người đề nghị', 'Family sponsor permanent / temporary address in Vietnam': 'Địa chỉ thường trú / tạm trú tại Việt Nam của người bảo lãnh', 'Family sponsor telephone / email': 'Điện thoại / email người bảo lãnh',
  'Request type': 'Loại đề nghị', 'Visa entry type': 'Số lần nhập cảnh', 'Requested visa valid until': 'Đề nghị thị thực có giá trị đến', 'Requested stay extension until': 'Đề nghị gia hạn tạm trú đến', 'Reason for the request': 'Lý do đề nghị', 'Additional statements': 'Nội dung trình bày thêm', 'Place of signing': 'Nơi ký', 'Date of signing': 'Ngày ký', 'Certification: signature, full name, title and stamp': 'Xác nhận: chữ ký, họ tên, chức vụ và con dấu', 'Sponsor signature and full name': 'Chữ ký và họ tên người bảo lãnh', 'Applicant signature and full name': 'Chữ ký và họ tên người đề nghị',
};
const options: Record<string, [string, string]> = { male: ['Nam', 'Male'], female: ['Nữ', 'Female'], organisation: ['Cơ quan / tổ chức', 'Organisation'], family: ['Người thân', 'Family'], vietnamese_citizen: ['Công dân Việt Nam', 'Vietnamese citizen'], foreign_resident: ['Người nước ngoài cư trú', 'Foreign resident'], visa_issuance: ['Cấp thị thực', 'Visa issuance'], stay_extension: ['Gia hạn tạm trú', 'Stay extension'], single: ['Một lần', 'Single entry'], multiple: ['Nhiều lần', 'Multiple entries'] };
/** For authored interface copy only. Never call on source wording, replies or entered values. */
export function translate(locale: Locale, text: string): string {
  const key = text.trim().replace(/\s+/g, ' '); const dictionary = english as Record<string, string>;
  const field = (label: string) => locale === 'vi' ? viFields[label] ?? label : label;
  let result: string | undefined = options[key]?.[locale === 'vi' ? 0 : 1] ?? (locale === 'vi' ? viFields[key] : dictionary[key]);
  if (key.includes(' + ') && key.split(' + ').every(part => dictionary[part])) result = key.split(' + ').map(part => translate(locale, part)).join(' + ');
  const next = /^Mục tiếp theo: (.*)\. Bạn vui lòng bổ sung thông tin này\.$/.exec(key);
  if (next) result = locale === 'en' ? `Next field: ${field(next[1])}. Please provide this information.` : `Mục tiếp theo: ${field(next[1])}. Bạn vui lòng bổ sung thông tin này.`;
  const required = /^Cần điền: (.*)$/.exec(key);
  if (required) result = locale === 'en' ? `Required: ${field(required[1])}` : `Cần điền: ${field(required[1])}`;
  const edit = /^Sửa (.*) ([0-9]+)$/.exec(key);
  if (edit) result = locale === 'en' ? `Edit ${field(edit[1])} ${edit[2]}` : `Sửa ${field(edit[1])} ${edit[2]}`;
  const proposal = /^Đề xuất (.*) · (.*)$/.exec(key);
  if (proposal) result = `${locale === 'en' ? 'Proposed' : 'Đề xuất'} ${field(proposal[1])} · ${translate(locale, proposal[2])}`;
  const fixturePrompt = /^Tình huống UI · Nhập dữ liệu giả cho: (.*)\.$/.exec(key);
  if (fixturePrompt) result = locale === 'en' ? `UI scenario · Enter fictional details for: ${field(fixturePrompt[1])}.` : `Tình huống UI · Nhập dữ liệu giả cho: ${field(fixturePrompt[1])}.`;
  const fixtureUpdate = /^Tình huống UI · Đã cập nhật bản nháp\.(?: Mục tiếp theo: (.*)\.)?$/.exec(key);
  if (fixtureUpdate) result = locale === 'en' ? `UI scenario · Draft updated.${fixtureUpdate[1] ? ` Next field: ${field(fixtureUpdate[1])}.` : ''}` : `Tình huống UI · Đã cập nhật bản nháp.${fixtureUpdate[1] ? ` Mục tiếp theo: ${field(fixtureUpdate[1])}.` : ''}`;
  if (locale === 'en') {
    const count = /^([0-9]+) mục của NA5 cần bổ sung$/.exec(key); if (count) result = `${count[1]} NA5 fields need details`;
    const max = /^Tối đa ([0-9]+) ký tự theo schema\.$/.exec(key); if (max) result = `Up to ${max[1]} characters for this field.`;
    const page = /^NA5 trang ([0-9]+) · bản nháp đang chờ duyệt$/.exec(key); if (page) result = `NA5 page ${page[1]} · draft awaiting review`;
    const preparation = /^Chuẩn bị mục nguồn ([0-9]+)$/.exec(key); if (preparation) result = `Prepare source entry ${preparation[1]}`;
    const confirmed = /^Bạn đã xác nhận (.*)\.$/.exec(key); if (confirmed) result = `You confirmed ${confirmed[1]}.`;
    const chosen = /^Bạn đã chọn (.*)\. Hiện chưa có quy trình điền tương thích cho thủ tục này\. Thông tin chỉ được mở để xem; không tự chọn biểu mẫu khác\.$/.exec(key); if (chosen) result = `You selected ${chosen[1]}. No compatible filling workflow is available. Information is view-only; no other form is selected automatically.`;
    const source = /^([^:]+): (.*)$/.exec(key); if (source && dictionary[source[1]] && dictionary[source[2]]) result = `${dictionary[source[1]]}: ${dictionary[source[2]]}`;
    if (source && ['Nguồn', 'Bản chụp nguồn', 'Thời điểm lấy nguồn', 'Phiên bản', 'Trạng thái mẫu'].includes(source[1])) result = `${dictionary[source[1]]}: ${source[2]}`;
    const catalog = /^Danh mục Vincent · (.*)$/.exec(key); if (catalog) result = `Vincent catalog · ${catalog[1]}`;
  }
  if (result === undefined) return text;
  return `${/^\s/.test(text) ? ' ' : ''}${result}${/\s$/.test(text) ? ' ' : ''}`;
}
