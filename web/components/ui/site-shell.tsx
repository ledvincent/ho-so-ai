'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ArrowUpRight, MessageCircle, Search, UserRound } from 'lucide-react';
import { Brand } from './brand';
import styles from './site-shell.module.css';

const destinations = [
  { href: '/workspace', label: 'Trợ lý hồ sơ', icon: MessageCircle },
  { href: '/research', label: 'Tra cứu', icon: Search },
  { href: '/portal', label: 'Hồ sơ của tôi', icon: UserRound },
];

/** Presentation only. Session verification stays in the existing Clerk pages/proxies. */
export function SiteShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isWorkspace = pathname === '/forms/demo' || pathname === '/demo/ct01' || pathname === '/workspace';
  const activeDestination = isWorkspace ? '/workspace' : pathname;
  return <div className={`${styles.frame} ${isWorkspace ? styles.compactWorkspace : ''}`}>
    <a className={styles.skip} href="#main-content">Đến nội dung chính</a>
    <aside className={styles.sidebar}>
      <Link className={styles.brandLink} href="/" aria-label="Hồ Sơ AI — trang bắt đầu"><Brand /></Link>
      <p className={styles.navLabel}>KHÔNG GIAN CỦA BẠN</p>
      <nav className={styles.navigation} aria-label="Điều hướng chính">
        {destinations.map(({ href, label, icon: Icon }) => <Link key={href} href={href} prefetch={false} aria-current={activeDestination === href ? 'page' : undefined} className={activeDestination === href ? styles.active : ''}><Icon size={19} aria-hidden="true" /><span>{label}</span></Link>)}
      </nav>
      <div className={styles.sideNote}><span className={styles.noteLine} /><b>Từng bước, theo cách của bạn.</b><p>Lưu hồ sơ để dùng lại, hoặc nhập trực tiếp vào một bản nháp.</p></div>
      <div className={styles.sideFoot}><span className={styles.dot} />Không gian thử nghiệm</div>
    </aside>
    <div className={styles.workspace}>
      <header className={styles.topbar}><span>HỒ SƠ AI <i>/</i> CHUẨN BỊ VÀ RÀ SOÁT</span><Link href="/portal" prefetch={false}>Tài khoản <ArrowUpRight size={15} aria-hidden="true" /></Link></header>
      {children}
      <footer className={styles.footer}><span>Hồ Sơ AI · Rõ ràng từng bước</span><span>Biểu mẫu thử nghiệm · Chỉ dùng dữ liệu giả</span></footer>
    </div>
  </div>;
}
