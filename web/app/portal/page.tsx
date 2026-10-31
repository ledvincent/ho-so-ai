import Link from 'next/link';
import { redirect } from 'next/navigation';
import { ArrowRight, FileText, RefreshCw, UserRound } from 'lucide-react';
import { verifiedSession } from '@/lib/server/clerk';
import { verifiedSession as appSession } from '@/lib/server/session';
import { identityFrom, isLocalProvider } from '@/lib/local-auth-policy';
import { AuthenticatedPortal } from '@/components/guided-portal/authenticated';
import { PortalSession } from '@/components/portal/profile-editor';
import { JourneyNav } from '@/components/ui/journey-nav';
import styles from '@/components/portal/portal.module.css';

export const dynamic = 'force-dynamic';
export default async function Portal() {
  if (isLocalProvider()) {
    const local = await appSession();
    const identity = identityFrom(local);
    if (local.status === 'signed-out') redirect('/login');
    if (local.status !== 'signed-in' || !identity) return <main className="auth-panel"><section className="card"><h1>Chưa thể kiểm tra phiên.</h1><a href="/portal">Thử lại</a></section></main>;
    return <AuthenticatedPortal session={identity} view="profile" />;
  }
  let session: Awaited<ReturnType<typeof verifiedSession>>;
  try {
    session = await verifiedSession();
  } catch {
    return <main id="main-content" lang="vi" className={styles.shell}>
      <JourneyNav current="profile" />
      <header className={styles.heading}><p className={styles.eyebrow}>HỒ SƠ AI · TÀI KHOẢN</p><h1>Hồ sơ của bạn.</h1><p>Chuẩn bị thông tin một lần, kiểm tra lại cho từng biểu mẫu.</p></header>
      <section className={styles.sessionPanel} aria-labelledby="session-title">
        <span className={styles.cardIcon}><UserRound size={24} aria-hidden="true" /></span>
        <h2 id="session-title">Chưa thể kiểm tra đăng nhập</h2>
        <p>Dịch vụ đăng nhập đang không khả dụng. Thông tin hồ sơ chưa được tải. Bạn có thể thử lại hoặc tiếp tục với biểu mẫu giả lập.</p>
        <div className={styles.sessionActions}>
          <a className={styles.primary} href="/portal"><RefreshCw size={16} aria-hidden="true" /> Thử lại</a>
          <Link className={styles.secondary} href="/forms/demo" prefetch={false}>Điền tay bằng dữ liệu mẫu <ArrowRight size={16} aria-hidden="true" /></Link>
        </div>
        <p className={styles.sessionFootnote}>Biểu mẫu thử nghiệm không yêu cầu hồ sơ đã lưu. Chỉ sử dụng thông tin giả lập.</p>
      </section>
    </main>;
  }
  return <main id="main-content" lang="vi" className={styles.shell}>
    <JourneyNav current="profile" />
    <header className={styles.heading}><p className={styles.eyebrow}>HỒ SƠ AI · TÀI KHOẢN</p><h1>Hồ sơ của bạn.</h1><p>Chuẩn bị thông tin một lần, kiểm tra lại cho từng biểu mẫu.</p></header>
    {session.status === 'unconfigured' ? <section className={styles.sessionPanel} aria-labelledby="session-title">
      <span className={styles.cardIcon}><FileText size={24} aria-hidden="true" /></span>
      <h2 id="session-title">Bạn vẫn có thể thử biểu mẫu</h2>
      <p>Đăng nhập chưa sẵn sàng trong môi trường này. Chưa có hồ sơ tài khoản nào được tải hoặc lưu.</p>
      <p>Tiếp tục bằng cách nhập tay. Bạn có thể xem lại biểu mẫu bằng thông tin giả lập, không cần tạo hồ sơ trước.</p>
      <div className={styles.sessionActions}>
        <Link className={styles.primary} href="/forms/demo" prefetch={false}>Điền tay bằng dữ liệu mẫu <ArrowRight size={16} aria-hidden="true" /></Link>
        <a className={styles.textButton} href="/portal"><RefreshCw size={15} aria-hidden="true" /> Kiểm tra lại đăng nhập</a>
      </div>
      <p className={styles.sessionFootnote}>Đây là biểu mẫu thử nghiệm, chưa phải biểu mẫu chính thức. Chỉ dùng dữ liệu mẫu.</p>
    </section>
      : session.status === 'signed-out' ? <section className={styles.sessionPanel} aria-labelledby="session-title">
        <span className={styles.cardIcon}><UserRound size={24} aria-hidden="true" /></span>
        <h2 id="session-title">Đăng nhập để mở hồ sơ</h2>
        <p>Dùng hồ sơ đã lưu trong tài khoản để chuẩn bị biểu mẫu. Bạn cũng có thể thử nhập tay mà không cần hồ sơ.</p>
        <div className={styles.sessionActions}>
          <Link className={styles.primary} href="/sign-in">Đăng nhập <ArrowRight size={16} aria-hidden="true" /></Link>
          <Link className={styles.secondary} href="/forms/demo" prefetch={false}>Điền tay bằng dữ liệu mẫu</Link>
        </div>
        <p className={styles.sessionFootnote}>Trong biểu mẫu thử nghiệm, chỉ sử dụng thông tin giả lập.</p>
      </section>
      : <PortalSession />}
  </main>;
}
