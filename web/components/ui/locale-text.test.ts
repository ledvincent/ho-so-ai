import test from 'node:test';
import assert from 'node:assert/strict';
import { translate, validLocale, LOCALE_KEY } from './locale-text';
import english from './locale-en.json';

test('VI is the safe default; the only saved preference key is a non-sensitive locale', () => {
  assert.equal(validLocale('en'), 'en'); assert.equal(validLocale('vi'), 'vi'); assert.equal(validLocale('other'), 'vi');
  assert.equal(LOCALE_KEY, 'hoso-ui-locale');
});
test('the full authored English dictionary is populated and interface copy switches both ways', () => {
  assert.ok(Object.keys(english).length > 200);
  for (const [key, value] of Object.entries(english)) { assert.ok(value.trim()); assert.equal(translate('en', key).trim(), value); }
  assert.equal(translate('vi', 'Lưu hồ sơ'), 'Lưu hồ sơ'); assert.equal(translate('en', 'Lưu hồ sơ'), 'Save profile');
  assert.equal(translate('vi', 'Full name (capital letters)'), 'Họ tên đầy đủ (chữ in hoa)');
});
test('local questions, source labels, bounds and controls translate without changing identifiers or values', () => {
  assert.equal(translate('en', 'Mục tiếp theo: Current nationality. Bạn vui lòng bổ sung thông tin này.'), 'Next field: Current nationality. Please provide this information.');
  assert.equal(translate('vi', 'Mục tiếp theo: Current nationality. Bạn vui lòng bổ sung thông tin này.'), 'Mục tiếp theo: Quốc tịch hiện nay. Bạn vui lòng bổ sung thông tin này.');
  assert.equal(translate('en', '12 mục của NA5 cần bổ sung'), '12 NA5 fields need details');
  assert.equal(translate('en', 'Số điện thoại + Email'), 'Phone number + Email');
  assert.equal(translate('en', 'NA5 trang 3 · bản nháp đang chờ duyệt'), 'NA5 page 3 · draft awaiting review');
  assert.equal(translate('en', 'Tối đa 100 ký tự theo schema.'), 'Up to 100 characters for this field.');
  assert.equal(translate('vi', 'Tình huống UI · Đã cập nhật bản nháp. Mục tiếp theo: Date of birth.'), 'Tình huống UI · Đã cập nhật bản nháp. Mục tiếp theo: Ngày sinh.');
});
test('unknown text, source wording, hashes and profile strings pass through unchanged; no locale goes on the wire', () => {
  for (const text of ['000012345', 'Nguyên văn: một bộ A hoặc B nếu đáp ứng điều kiện.', 'fixture@example.test', 'a17ded2807db3f51347d55b9a5e2cac9d58d58de3c4510786a34b951e8184751']) assert.equal(translate('en', text), text);
  assert.equal(translate('en', 'Bạn đã xác nhận Gia hạn tạm trú cho người nước ngoài (cấp tỉnh) (1.001146).'), 'You confirmed Gia hạn tạm trú cho người nước ngoài (cấp tỉnh) (1.001146).');
});
