import { SignUp } from '@clerk/nextjs';
import { clerkConfigured } from '@/lib/server/clerk';
import Link from 'next/link';
import { BrandMark } from '@/components/ui/brand';
export default function SignUpPage() {
  return <main id="main-content" className="auth-panel">{clerkConfigured() ? <SignUp fallbackRedirectUrl="/workspace" /> : <section className="card auth-unavailable"><BrandMark /><p className="eyebrow">TÀI KHOẢN HỒ SƠ AI</p><h1>Chưa thể tạo tài khoản.</h1><p>Dịch vụ đăng nhập chưa được kết nối trong môi trường này. Bạn có thể thử biểu mẫu mà không tạo hồ sơ tài khoản.</p><Link className="button primary" href="/forms/demo" prefetch={false}>Thử biểu mẫu với dữ liệu giả</Link><Link className="auth-back" href="/">Về trang bắt đầu</Link></section>}</main>;
}
