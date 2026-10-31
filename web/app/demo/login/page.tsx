'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { BrandMark } from '@/components/ui/brand';
import { useDemoSession } from '@/components/ct01-demo/demo-session';
import styles from '@/components/ct01-demo/demo-session.module.css';

export default function DemoLogin() {
  const session = useDemoSession();
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [failed, setFailed] = useState(false);
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const accepted = session.enter(username, password);
    setPassword(''); setFailed(!accepted);
    if (accepted) router.replace('/demo/workspace');
  }
  return <main id="main-content" className={styles.login}><section className={styles.card}>
    <BrandMark /><p className="eyebrow">DEMO · DỮ LIỆU GIẢ</p><h1>Mở không gian thử.</h1>
    <p>Phiên minh họa trong thẻ này. Không mở hoặc lưu hồ sơ tài khoản thật.</p>
    <p className={styles.credentials}>Tên đăng nhập: <b>admin</b> · Mật khẩu: <b>admin</b></p>
    <form onSubmit={submit} autoComplete="off">
      <label htmlFor="demo-username">Tên đăng nhập demo</label><input id="demo-username" value={username} onChange={event => setUsername(event.target.value)} autoComplete="off" autoCapitalize="none" spellCheck={false} required />
      <label htmlFor="demo-password">Mật khẩu demo</label><input id="demo-password" type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="off" required />
      {failed && <p className={styles.error} role="alert">Thông tin demo chưa đúng. Dùng admin / admin.</p>}
      <button className="button primary" type="submit">Vào bản demo</button>
    </form>
    <Link className={styles.realLogin} href="/sign-in">Mở đăng nhập tài khoản thật</Link>
  </section></main>;
}
