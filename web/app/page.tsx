import Link from 'next/link';
import { ArrowRight, Info } from 'lucide-react';
import { BrandMark } from '@/components/ui/brand';
import { clerkConfigured } from '@/lib/server/clerk';
import styles from './home.module.css';
export default function Home() {
  const configured = clerkConfigured();
  return <main id="main-content" className={styles.main}>
    <div className={styles.hero}>
      <section className={styles.intro}><p className="eyebrow">HỒ SƠ CỦA BẠN, TỪNG BƯỚC RÕ RÀNG</p><h1>Thêm hướng dẫn.<br />Rõ bước tiếp theo.</h1><p>Chuẩn bị thông tin, tạo một bản nháp và kiểm tra từng chi tiết trước khi tải PDF.</p><div className={styles.features}><span><b>01</b>Hồ sơ chỉ cập nhật khi bạn lưu</span><span><b>02</b>Bản nháp được chỉnh sửa riêng</span><span><b>03</b>Rà soát trước mỗi lần tải PDF</span></div></section>
      <section className={styles.welcome} aria-labelledby="welcome-title"><BrandMark /><h2 id="welcome-title">Bắt đầu từ đây.</h2><p>Dùng hồ sơ tài khoản để điền nhanh hơn, hoặc tự nhập thông tin cho từng biểu mẫu.</p><Link className="button primary" href="/workspace" prefetch={false}>Vào không gian cá nhân <ArrowRight size={17} aria-hidden="true" /></Link><Link className={`button ${styles.manual}`} href="/demo/ct01" prefetch={false}>Thử CT01 với dữ liệu giả</Link><p className={styles.fine}>{configured ? 'Hồ sơ tài khoản yêu cầu đăng nhập. Biểu mẫu hiện tại là bản thử nghiệm; chỉ dùng dữ liệu giả.' : 'Đăng nhập chưa được kết nối trong môi trường này. Bạn vẫn có thể thử nhập biểu mẫu bằng dữ liệu giả.'}</p></section>
    </div>
    <div className={styles.sectionHead}><h2>Một hành trình, ba bước.</h2><p>Bạn luôn có thể nhập trực tiếp.</p></div>
    <div className={styles.steps}><section className={styles.step}><span>01 / HỒ SƠ TÀI KHOẢN</span><h3>Chuẩn bị một lần.</h3><p>Lưu thông tin bạn muốn dùng lại. Mỗi thay đổi cần được lưu rõ ràng trước khi chuyển sang biểu mẫu.</p></section><section className={styles.step}><span>02 / BẢN NHÁP BIỂU MẪU</span><h3>Điều chỉnh cho lần này.</h3><p>Sao chép hồ sơ hoặc nhập bằng tay. Chỉnh sửa bản nháp không thay đổi hồ sơ đã lưu.</p></section><section className={styles.step}><span>03 / RÀ SOÁT & PDF</span><h3>Kiểm tra, rồi tải xuống.</h3><p>Xem bản nháp, xác nhận đã rà soát và tải PDF. Sau mỗi lần sửa, hãy cập nhật bản xem trước.</p></section></div>
    <div className={styles.note}><Info size={18} aria-hidden="true" /><p>Không gian này chỉ thử điền dữ liệu giả. Mẫu CT01 chưa được duyệt để sử dụng trong hệ thống chính thức; ứng dụng không nộp hồ sơ đến cơ quan tiếp nhận.</p></div>
  </main>;
}
