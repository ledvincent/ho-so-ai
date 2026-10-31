import Link from 'next/link';
import { verifiedSession } from '@/lib/server/clerk';
import { PortalSession } from '@/components/portal/profile-editor';
import styles from '@/components/portal/portal.module.css';

export const dynamic = 'force-dynamic';
export default async function Portal() {
  let session: Awaited<ReturnType<typeof verifiedSession>>;
  try {
    session = await verifiedSession();
  } catch {
    return <main lang="vi" className={styles.shell}><section className={styles.sessionPanel}><p className={styles.eyebrow}>HỒ SƠ CÁ NHÂN</p><h1>Chưa thể kiểm tra đăng nhập</h1><p>Dịch vụ đăng nhập đang không khả dụng. Thông tin hồ sơ chưa được tải.</p><Link className={styles.secondary} href="/portal" prefetch={false}>Thử lại</Link></section></main>;
  }
  return <main lang="vi" className={styles.shell}>
    <header className={styles.heading}><p className={styles.eyebrow}>HỒ SƠ AI · TÀI KHOẢN</p><h1>Hồ sơ của bạn.</h1><p>Chuẩn bị thông tin một lần, kiểm tra lại cho từng biểu mẫu.</p></header>
    {session.status === 'unconfigured' ? <section className={styles.sessionPanel}><h2>Đăng nhập chưa sẵn sàng</h2><p>Môi trường này chưa kết nối dịch vụ đăng nhập. Chưa có hồ sơ tài khoản nào được tải hoặc lưu.</p><p>Chỉ dùng thông tin giả lập khi thử nghiệm.</p><Link className={styles.secondary} href="/forms/demo" prefetch={false}>Mở biểu mẫu thử nghiệm</Link></section>
      : session.status === 'signed-out' ? <section className={styles.sessionPanel}><h2>Đăng nhập để mở hồ sơ</h2><p>Hồ sơ được tải từ tài khoản đang đăng nhập.</p><Link className={styles.primary} href="/sign-in">Đăng nhập</Link></section>
      : <PortalSession />}
  </main>;
}
