'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { BrandMark } from '@/components/ui/brand';
import styles from './portal.module.css';

export function PortalLogin({ authenticate, notice }: { authenticate?: (username: string, password: string, signal: AbortSignal) => Promise<void>; notice?: string }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || !authenticate) return;
    request.current?.abort(); const attempt = new AbortController(); request.current = attempt;
    setBusy(true); setError('');
    try { await authenticate(username.trim(), password, attempt.signal); }
    catch { if (!attempt.signal.aborted) { setError('Không thể đăng nhập. Kiểm tra thông tin và thử lại.'); setPassword(''); } }
    finally { if (!attempt.signal.aborted) setBusy(false); }
  }
  return <main id="main-content" className={styles.loginPage}>
    <section className={styles.loginCard}><BrandMark /><p className={styles.wordmark}>Hồ Sơ <span>AI</span></p><h1>Hồ sơ của bạn,<br />từng câu hỏi một.</h1><p className={styles.intro}>Đăng nhập để cùng trợ lý chuẩn bị biểu mẫu.</p>
      <form onSubmit={submit} aria-label="Đăng nhập"><label htmlFor="portal-username">Tên đăng nhập</label><input id="portal-username" name="username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required maxLength={120} disabled={busy} /><label htmlFor="portal-password">Mật khẩu</label><input id="portal-password" name="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required maxLength={256} disabled={busy} />{error && <p role="alert" className={styles.error}>{error}</p>}<button className={styles.primary} disabled={!authenticate || busy || !username.trim() || !password}>{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button></form>
      {notice && <p className={styles.boundary}>{notice}</p>}
    </section><p className={styles.loginFoot}>Rõ ràng từng bước.</p>
  </main>;
}
