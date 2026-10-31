'use client';

import Link from 'next/link';
import { GuidedWorkbench } from '@/components/guided-portal/workbench';
import { useDemoSession } from '@/components/ct01-demo/demo-session';
import styles from '@/components/ct01-demo/demo-session.module.css';

export default function DemoWorkspace() {
  const session = useDemoSession();
  if (!session.active) return <main id="main-content" className={styles.login}><section className={styles.card}><p className="eyebrow">DEMO</p><h1>Mở phiên thử nghiệm.</h1><p>Phiên demo chưa mở hoặc đã kết thúc. Bản nháp từ phiên trước không được giữ lại.</p><Link className="button primary" href="/demo/login">Đăng nhập demo</Link></section></main>;
  return <GuidedWorkbench key={session.epoch} username="Prototype" adapter={null} logout={async () => session.leave()} onExpired={session.leave} provisional />;
}
