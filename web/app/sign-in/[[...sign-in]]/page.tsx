import { SignIn } from '@clerk/nextjs';
import { clerkConfigured } from '@/lib/server/clerk';
import Link from 'next/link';
import { BrandMark } from '@/components/ui/brand';
export default function SignInPage() {
  return <main id="main-content" className="auth-panel">{clerkConfigured() ? <SignIn fallbackRedirectUrl="/workspace" /> : <section className="card auth-unavailable"><BrandMark /><p className="eyebrow">TÀI KHOẢN HỒ SƠ AI</p><h1>Đăng nhập chưa sẵn sàng.</h1><p>Môi trường này chưa kết nối dịch vụ đăng nhập. Chưa có hồ sơ tài khoản nào được tải hoặc lưu.</p><Link className="button primary" href="/forms/demo" prefetch={false}>Thử biểu mẫu với dữ liệu giả</Link><Link className="auth-back" href="/">Về trang bắt đầu</Link></section>}</main>;
}
