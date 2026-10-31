'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { RichProfileEditor } from '@/components/saved-profile/editor';
import { createProfileClient } from '@/components/saved-profile/api';
import { createGuidedAdapter, logoutRequest, sameSession, sessionRequest, type LocalSession } from './api';
import { ProcedureChat } from '@/components/procedure-chat/chat';
import { createDiscoveryAdapter } from '@/components/procedure-chat/api';
import styles from './portal.module.css';

/** Server guard supplies this public session view; it contains no credential. */
export function AuthenticatedPortal({ session, view = 'workspace', fixtures = false }: { session: LocalSession; view?: 'workspace' | 'profile'; fixtures?: boolean }) {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const live = useRef(true);
  const adapter = useMemo(() => createGuidedAdapter(session), [session.user.id, session.expires_at]);
  const discovery = useMemo(() => createDiscoveryAdapter(session), [session.user.id, session.expires_at]);
  const profile = useMemo(() => createProfileClient(session), [session.user.id, session.expires_at]);
  const expire = () => { if (!live.current) return; live.current = false; setReady(false); window.location.replace('/login'); };
  useEffect(() => {
    live.current = true; const controller = new AbortController();
    async function check(initial = false) {
      try {
        const current = await sessionRequest(controller.signal);
        if (!sameSession(session, current)) { expire(); return; }
        if (live.current) { setReady(true); setFailed(false); }
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error instanceof Error && error.name === 'SessionExpired') expire();
        else if (live.current) { setReady(false); setFailed(true); }
      }
    }
    void check(true);
    const focus = () => { if (document.visibilityState === 'visible') void check(); };
    window.addEventListener('focus', focus); document.addEventListener('visibilitychange', focus);
    const expiryMs = session.expires_at < 1e12 ? session.expires_at * 1000 : session.expires_at;
    const timer = setTimeout(expire, Math.max(0, Math.min(expiryMs - Date.now(), 2147483647)));
    return () => { live.current = false; controller.abort(); clearTimeout(timer); window.removeEventListener('focus', focus); document.removeEventListener('visibilitychange', focus); };
  }, [session.user.id, session.expires_at]);
  if (!ready) return <main className={styles.loginPage}><section className={styles.loginCard}><h1>{failed ? 'Chưa thể kiểm tra phiên.' : 'Đang mở không gian của bạn…'}</h1>{failed && <><p>Bản nháp đã được xóa khỏi màn hình. Kiểm tra lại kết nối.</p><button type="button" className={styles.primary} onClick={() => window.location.reload()}>Thử lại</button></>}</section></main>;
  if (view === 'profile') return <main id="main-content" className={styles.profilePage}><Link href="/workspace" prefetch={false}>← Trợ lý hồ sơ</Link><h1>Hồ sơ của bạn</h1><RichProfileEditor key={`${session.user.id}:${session.expires_at}`} client={profile} onExpired={expire} onLogout={async () => { setReady(false); try { await logoutRequest(); expire(); } catch { setFailed(true); } }} /></main>;
  return <ProcedureChat key={`${session.user.id}:${session.expires_at}`} username={session.user.username} formAdapter={adapter} discovery={discovery} profile={{ client: profile.prefill, session: `${session.user.id}:${session.expires_at}` }} logout={logoutRequest} onExpired={expire} fixtures={fixtures} />;
}
