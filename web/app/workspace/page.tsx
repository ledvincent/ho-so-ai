import Link from 'next/link';
import { redirect } from 'next/navigation';
import { verifiedSession } from '@/lib/server/clerk';
import { AccountWorkbench } from '@/components/forms/account-workbench';
import { BrandMark } from '@/components/ui/brand';

export const dynamic = 'force-dynamic';
export default async function Workspace() {
  let session: Awaited<ReturnType<typeof verifiedSession>>;
  try { session = await verifiedSession(); }
  catch { return <main id="main-content" className="auth-panel"><section className="card auth-unavailable"><BrandMark /><h1>Chưa thể kiểm tra phiên đăng nhập.</h1><p>Hồ sơ tài khoản chưa được tải. Hãy thử lại khi dịch vụ sẵn sàng.</p><a className="button primary" href="/workspace">Thử lại</a><Link className="auth-back" href="/demo/ct01" prefetch={false}>Mở không gian thử nghiệm riêng</Link></section></main>; }
  if (session.status === 'signed-out') redirect('/sign-in');
  if (session.status === 'unconfigured') return <main id="main-content" className="auth-panel"><section className="card auth-unavailable"><BrandMark /><p className="eyebrow">KHÔNG GIAN CÁ NHÂN</p><h1>Đăng nhập chưa sẵn sàng.</h1><p>Không gian cá nhân cần phiên đăng nhập. Bạn có thể xem giao diện trong không gian thử nghiệm riêng với dữ liệu giả, không có hồ sơ tài khoản.</p><Link className="button primary" href="/demo/ct01" prefetch={false}>Thử CT01 với dữ liệu giả</Link><Link className="auth-back" href="/">Về trang bắt đầu</Link></section></main>;
  return <AccountWorkbench />;
}
