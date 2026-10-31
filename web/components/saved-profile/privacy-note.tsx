import styles from './profile.module.css';

export function PrivacyNote() {
  return <details className={styles.privacy}><summary>Thông tin riêng tư trong bản thử nghiệm</summary><p>Chỉ dùng thông tin giả lập; tránh nhập thông tin nhạy cảm thật. Nội dung bạn gõ vào trò chuyện có thể được gửi đến dịch vụ AI hoặc tra cứu khi được kết nối. Khi điền tài liệu, hồ sơ đã lưu chỉ được đọc sau khi bạn chọn dùng hồ sơ và xác nhận mình là người đề nghị. Bước đề xuất sao chép hồ sơ xử lý xác định, không gọi mô hình. Bạn kiểm tra các đề xuất trước khi áp dụng. Sửa bản nháp không tự lưu lại hồ sơ; hồ sơ chỉ được cập nhật bằng nút “Lưu hồ sơ”.</p></details>;
}
