'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { flushSync } from 'react-dom';
import { useRouter } from 'next/navigation';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import styles from './demo-session.module.css';

type DemoSession = { active: boolean; epoch: number; enter: (username: string, password: string) => boolean; leave: () => void };
const Context = createContext<DemoSession | null>(null);

/** Synthetic UI session only: no token, cookie, storage, Clerk or profile request. */
export function DemoSessionProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  const [epoch, setEpoch] = useState(0);
  const router = useRouter();
  function clear() { setActive(false); setEpoch(value => value + 1); }
  useEffect(() => listenForProfilePageLifecycle(window, () => flushSync(clear), () => {}), []);
  function enter(username: string, password: string) {
    if (username !== 'admin' || password !== 'admin') return false;
    setEpoch(value => value + 1); setActive(true); return true;
  }
  function leave() { flushSync(clear); router.replace('/demo/login'); }
  return <Context.Provider value={{ active, epoch, enter, leave }}>
    {active && <div className={styles.bar}><span><b>Demo</b> · admin · dữ liệu giả</span><button type="button" onClick={leave}>Đăng xuất demo</button></div>}
    {children}
  </Context.Provider>;
}

export function useDemoSession() {
  const session = useContext(Context);
  if (!session) throw new Error('Demo session requires the scoped demo layout.');
  return session;
}
