import Link from 'next/link';
import styles from './journey-nav.module.css';

export function JourneyNav({ current }: { current: 'profile' | 'form' }) {
  return <nav className={styles.journey} aria-label="Các bước chuẩn bị">
    <Link href="/portal" prefetch={false} aria-current={current === 'profile' ? 'step' : undefined}><span>01</span>Hồ sơ tài khoản<small>Tùy chọn</small></Link>
    <i aria-hidden="true">/</i>
    <Link href="/forms/demo" prefetch={false} aria-current={current === 'form' ? 'step' : undefined}><span>02</span>Bản nháp biểu mẫu</Link>
    <i aria-hidden="true">/</i>
    <Link href="/forms/demo#document-review" prefetch={false}><span>03</span>Rà soát & PDF</Link>
  </nav>;
}
