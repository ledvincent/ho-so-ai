'use client';
import { useEffect, useSyncExternalStore } from 'react';
import { LOCALE_KEY, translate, validLocale, type Locale } from './locale-text';
import styles from './locale.module.css';

let locale: Locale = 'vi';
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
function publish(next: Locale) { locale = next; document.documentElement.lang = next; listeners.forEach(listener => listener()); }
function choose(next: Locale) { try { localStorage.setItem(LOCALE_KEY, next); } catch { /* Device preference remains in memory when storage is unavailable. */ } publish(next); }
export function useLocale() {
  const current = useSyncExternalStore(subscribe, () => locale, () => 'vi' as Locale);
  useEffect(() => {
    try { publish(validLocale(localStorage.getItem(LOCALE_KEY))); } catch { document.documentElement.lang = locale; }
    const changed = (event: StorageEvent) => { if (event.key === LOCALE_KEY) publish(validLocale(event.newValue)); };
    window.addEventListener('storage', changed); return () => window.removeEventListener('storage', changed);
  }, []);
  return { locale: current, t: (text: string) => translate(current, text) };
}
export function LocaleToggle({ compact = false }: { compact?: boolean }) {
  const { locale } = useLocale();
  return <div className={styles.toggle} role="group" aria-label={locale === 'vi' ? 'Ngôn ngữ giao diện' : 'Interface language'}><button type="button" aria-label="Tiếng Việt" title="Tiếng Việt" aria-pressed={locale === 'vi'} onClick={() => choose('vi')}>{compact ? 'VI' : 'Tiếng Việt'}</button><button type="button" aria-label="English" title="English" aria-pressed={locale === 'en'} onClick={() => choose('en')}>{compact ? 'EN' : 'English'}</button></div>;
}
export function LocalizedStatus({ retry }: { retry: '/portal' | '/workspace' }) {
  const { t } = useLocale();
  return <main className="auth-panel"><section className="card"><LocaleToggle /><h1>{t('Chưa thể kiểm tra phiên.')}</h1><a href={retry}>{t('Thử lại')}</a></section></main>;
}
