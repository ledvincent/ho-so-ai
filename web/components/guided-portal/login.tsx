'use client';
import { useLocale, LocaleToggle } from '@/components/ui/locale';


import { useEffect, useRef, useState, type FormEvent } from 'react';
import { BrandMark } from '@/components/ui/brand';
import styles from './portal.module.css';

export function PortalLogin({ authenticate, notice }: { authenticate?: (username: string, password: string, signal: AbortSignal) => Promise<void>; notice?: string }) {
  const { t } = useLocale();
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
    try { await authenticate(username.trim(), password, attempt.signal); setPassword(''); }
    catch { if (!attempt.signal.aborted) { setError('Không thể đăng nhập. Kiểm tra thông tin và thử lại.'); setPassword(''); } }
    finally { if (!attempt.signal.aborted) setBusy(false); }
  }
  return <main id="main-content" className={styles.loginPage}>
    <section className={styles.loginCard}><div style={{display:"flex",justifyContent:"flex-end",marginBottom:20}}><LocaleToggle /></div><BrandMark /><p className={styles.wordmark}>{t("Hồ Sơ ")}<span>{t("AI")}</span></p><h1>{t("Hồ sơ của bạn,")}<br />{t("từng câu hỏi một.")}</h1><p className={styles.intro}>{t("Đăng nhập để cùng trợ lý chuẩn bị biểu mẫu.")}</p>
      <form onSubmit={submit} aria-label={t("Đăng nhập")}><label htmlFor="portal-username">{t("Tên đăng nhập")}</label><input id="portal-username" name="username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required maxLength={120} disabled={busy} /><label htmlFor="portal-password">{t("Mật khẩu")}</label><input id="portal-password" name="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} required maxLength={256} disabled={busy} />{error && <p role="alert" className={styles.error}>{t(error)}</p>}<button className={styles.primary} disabled={!authenticate || busy || !username.trim() || !password}>{busy ? t("Đang đăng nhập…") : t("Đăng nhập")}</button></form>
      {notice && <p className={styles.boundary}>{t(notice)}</p>}
    </section><p className={styles.loginFoot}>{t("Rõ ràng từng bước.")}</p>
  </main>;
}
