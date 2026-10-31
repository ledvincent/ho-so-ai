'use client';
import { useAuth } from '@clerk/nextjs';
import { FormWorkbench } from './form-workbench';
import { JourneyNav } from '@/components/ui/journey-nav';
import styles from './form-workbench.module.css';
export function AccountWorkbench() {
  const { userId, sessionId, isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <main id="main-content" lang="vi" className={styles.main}>
    <JourneyNav current="form" />
    <section className={styles.sessionPanel} aria-live="polite" aria-busy="true">
      <h1>Chuẩn bị biểu mẫu</h1><p>Đang kiểm tra phiên đăng nhập…</p>
    </section>
  </main>;
  const signedIn = Boolean(isSignedIn && userId && sessionId);
  // Every account OR session transition remounts an empty draft and cancels old work.
  const accountKey = signedIn ? `${userId}:${sessionId}` : 'anonymous';
  return <FormWorkbench key={accountKey} accountState={signedIn ? 'signed-in' : 'signed-out'} accountKey={accountKey} />;
}
