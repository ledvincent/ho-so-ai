'use client';

import { useAuth } from '@clerk/nextjs';
import Link from 'next/link';
import { ArrowRight, Check, FileText, LogOut, RefreshCw, Save, UserRound } from 'lucide-react';
import { useEffect, useState, useSyncExternalStore, type FormEvent } from 'react';
import { flushSync } from 'react-dom';
import { PROFILE_LIMITS, type ProfileFields } from '../../lib/contracts';
import { PROFILE_MESSAGES, ProfileController } from './profile-state';
import { listenForProfilePageLifecycle } from './page-lifecycle';
import styles from './portal.module.css';

const fields: { key: keyof ProfileFields; label: string; type?: string; hint?: string }[] = [
  { key: 'full_name', label: 'Họ và tên', hint: 'Nhập theo giấy tờ bạn sẽ sử dụng.' },
  { key: 'date_of_birth', label: 'Ngày sinh', type: 'date' },
  { key: 'nationality', label: 'Quốc tịch' },
  { key: 'phone_number', label: 'Số điện thoại', type: 'tel' },
  { key: 'email', label: 'Email', type: 'email' },
  { key: 'address', label: 'Địa chỉ', hint: 'Có thể xuống dòng để ghi địa chỉ đầy đủ.' },
];

/** Clerk client state only controls clearing/display; the shared proxy authenticates every request. */
export function PortalSession() {
  const { isLoaded, isSignedIn, userId, sessionId, signOut } = useAuth();
  const [closing, setClosing] = useState(false);
  const [logoutFailed, setLogoutFailed] = useState(false);

  async function logout() {
    setClosing(true);
    setLogoutFailed(false);
    try {
      await signOut({ redirectUrl: '/' });
    } catch {
      // Never restore the old profile after a failed logout request.
      setLogoutFailed(true);
    }
  }

  if (closing) return <section className={styles.sessionPanel} aria-live="polite">
    <span className={styles.cardIcon}><LogOut size={23} aria-hidden="true" /></span>
    <h2>{logoutFailed ? 'Chưa thể xác nhận đăng xuất' : 'Đang đăng xuất…'}</h2>
    <p>Thông tin hồ sơ đã được đóng trên trang này.</p>
    {logoutFailed && <div className={styles.sessionActions}><button className={styles.secondary} onClick={() => void logout()}><RefreshCw size={16} aria-hidden="true" /> Thử đăng xuất lại</button></div>}
  </section>;
  if (!isLoaded) return <section className={styles.sessionPanel} aria-live="polite" aria-busy="true"><span className={styles.cardIcon}><UserRound size={23} aria-hidden="true" /></span><h2>Đang mở hồ sơ của bạn…</h2><p>Đang kiểm tra phiên đăng nhập trước khi tải thông tin.</p></section>;
  if (!isSignedIn || !userId || !sessionId) return <section className={styles.sessionPanel}>
    <span className={styles.cardIcon}><UserRound size={23} aria-hidden="true" /></span>
    <h2>Đăng nhập để mở hồ sơ</h2>
    <p>Thông tin từ phiên trước không được giữ lại trên trang này. Đăng nhập lại để tiếp tục với hồ sơ của bạn.</p>
    <div className={styles.sessionActions}>
      <Link className={styles.primary} href="/sign-in">Đăng nhập <ArrowRight size={17} aria-hidden="true" /></Link>
      <Link className={styles.secondary} href="/forms/demo" prefetch={false}>Điền tay bằng dữ liệu mẫu</Link>
    </div>
    <p className={styles.sessionFootnote}>Biểu mẫu thử nghiệm chỉ dành cho thông tin giả lập.</p>
  </section>;

  // A new account OR a new session mounts a fresh editor with no prior values.
  return <ProfileEditor key={`${userId}:${sessionId}`} onLogout={logout} />;
}

export function ProfileEditor({ onLogout, formHref = '/forms/demo', prefillAvailable = true }: { onLogout: () => Promise<void>; formHref?: string; prefillAvailable?: boolean }) {
  const [controller] = useState(() => new ProfileController());
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot, controller.snapshot);
  const [confirmReload, setConfirmReload] = useState(false);

  useEffect(() => {
    const stopPageLifecycle = listenForProfilePageLifecycle(
      window,
      // Commit the empty inputs to the DOM before the browser freezes this page.
      () => flushSync(() => controller.reset()),
      () => { void controller.load(); },
    );
    void controller.load();
    return () => {
      stopPageLifecycle();
      controller.reset();
    };
  }, [controller]);

  const busy = state.phase === 'loading' || state.phase === 'saving';
  const editable = state.phase === 'ready';
  const needsReload = state.problem === 'conflict' || state.problem === 'not-found';
  const canSave = editable && state.dirty && !needsReload;

  function reload() {
    if (state.dirty && !confirmReload) { setConfirmReload(true); return; }
    setConfirmReload(false);
    void controller.load();
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void controller.save();
  }

  return <>
    <div className={styles.toolbar}>
      <span className={styles.accountBadge}><UserRound size={15} aria-hidden="true" /> Hồ sơ tài khoản</span>
      <button className={styles.textButton} onClick={() => { controller.reset(); void onLogout(); }}><LogOut size={16} aria-hidden="true" /> Đăng xuất</button>
    </div>
    <div className={styles.columns}>
      <section className={styles.profileCard} aria-labelledby="profile-title" aria-busy={busy}>
        <div className={styles.cardHeading}>
          <div><p className={styles.eyebrow}>THÔNG TIN DÙNG LẠI</p><h2 id="profile-title">Hồ sơ cá nhân</h2></div>
          <span className={styles.optional}>Không bắt buộc</span>
        </div>
        <p className={styles.intro}>Điền những thông tin bạn muốn dùng lại. Hồ sơ chỉ được lưu khi bạn chọn “Lưu hồ sơ” và nhận được xác nhận.</p>
        {state.phase === 'loading' && <p className={styles.notice} role="status">Đang tải hồ sơ…</p>}
        {state.revision === 0 && <p className={styles.notice}>Bạn chưa có hồ sơ đã lưu. Có thể để trống những thông tin chưa cần dùng.</p>}
        {state.problem && <div className={styles.error} role="alert">
          <h3>{needsReload ? 'Cần tải lại hồ sơ' : state.problem === 'signed-out' ? 'Phiên đăng nhập đã kết thúc' : state.problem === 'invalid' ? 'Kiểm tra lại thông tin' : 'Chưa thể hoàn tất'}</h3>
          <p>{PROFILE_MESSAGES[state.problem]}</p>
          {state.problem === 'signed-out' && <Link className={styles.inlineLink} href="/sign-in">Đăng nhập lại <ArrowRight size={15} aria-hidden="true" /></Link>}
          {state.phase === 'blocked' && state.problem !== 'signed-out' && <button className={styles.inlineLink} type="button" onClick={reload}><RefreshCw size={15} aria-hidden="true" /> Thử tải lại hồ sơ</button>}
        </div>}
        <form onSubmit={submit} autoComplete="off">
          <fieldset className={styles.fieldset} disabled={!editable}>
            <legend className={styles.srOnly}>Thông tin hồ sơ</legend>
            <div className={styles.fieldGrid}>
              {fields.map(({ key, label, type = 'text', hint }) => <div className={`${styles.field} ${key === 'address' ? styles.wideField : ''}`} key={key}>
                <label htmlFor={`profile-${key}`}>{label}</label>
                {key === 'address'
                  ? <textarea id={`profile-${key}`} name={key} rows={3} value={state.fields[key] ?? ''} onChange={(event) => controller.edit(key, event.target.value)} maxLength={PROFILE_LIMITS[key]} aria-describedby={hint ? `hint-${key}` : undefined} />
                  : <input id={`profile-${key}`} name={key} type={type} value={state.fields[key] ?? ''} onChange={(event) => controller.edit(key, event.target.value)} maxLength={PROFILE_LIMITS[key]} aria-describedby={hint ? `hint-${key}` : undefined} />}
                {hint && <small id={`hint-${key}`}>{hint}</small>}
              </div>)}
            </div>
          </fieldset>
          <div className={styles.saveBar}>
            <p role="status" aria-live="polite">{state.phase === 'loading' || state.phase === 'idle' ? 'Đang tải thông tin hồ sơ…' : state.phase === 'saving' ? 'Đang lưu thay đổi…' : state.problem ? 'Chưa có xác nhận lưu thay đổi.' : state.saved ? <><Check size={16} aria-hidden="true" /> Đã lưu hồ sơ.</> : state.dirty ? 'Có thay đổi chưa lưu.' : state.revision && state.revision > 0 ? 'Đang xem hồ sơ đã lưu.' : 'Chưa có hồ sơ đã lưu.'}</p>
            <button className={styles.primary} type="submit" disabled={!canSave}><Save size={16} aria-hidden="true" /> {state.phase === 'saving' ? 'Đang lưu…' : 'Lưu hồ sơ'}</button>
          </div>
        </form>
        <div className={styles.recovery}>
          <button className={styles.textButton} disabled={busy || state.problem === 'signed-out'} onClick={reload}><RefreshCw size={14} aria-hidden="true" /> Tải lại hồ sơ</button>
          {state.dirty && !needsReload && <button className={styles.textButton} disabled={busy} onClick={() => { controller.discard(); setConfirmReload(false); }}>Bỏ thay đổi</button>}
        </div>
        {confirmReload && <div className={styles.confirm} role="group" aria-label="Xác nhận bỏ thay đổi">
          <p>Tải lại sẽ bỏ các thay đổi chưa lưu trên trang này.</p>
          <button className={styles.secondary} onClick={reload}>Bỏ thay đổi và tải lại</button>
          <button className={styles.textButton} onClick={() => setConfirmReload(false)}>Tiếp tục chỉnh sửa</button>
        </div>}
      </section>
      <aside className={styles.sidebar}>
        <section className={styles.nextCard} aria-labelledby="next-step-title">
          <span className={styles.cardIcon}><FileText size={23} aria-hidden="true" /></span>
          <p className={styles.eyebrow}>BƯỚC TIẾP THEO</p>
          <h2 id="next-step-title">Chuẩn bị biểu mẫu</h2>
          <p id="form-profile-note">{prefillAvailable ? 'Trong biểu mẫu, bạn có thể nhập tay hoặc chọn sao chép thông tin từ hồ sơ đã lưu. Bạn sẽ kiểm tra lại trước khi xuất bản nháp.' : 'Trợ lý chuẩn bị bản nháp NA5 riêng. Thông tin trong hồ sơ này chưa được sao chép sang NA5.'}</p>
          {state.dirty && <p className={styles.unsavedNote} id="unsaved-profile-note">Bạn có thay đổi chưa lưu. Nếu rời trang, các thay đổi này sẽ không được giữ lại hoặc chuyển sang biểu mẫu. Chỉ hồ sơ đã lưu mới được sao chép.</p>}
          <Link className={styles.primary} href={formHref} prefetch={false} aria-describedby={state.dirty ? 'unsaved-profile-note' : 'form-profile-note'}>{state.dirty ? 'Mở biểu mẫu, không lưu thay đổi' : 'Tiếp tục đến biểu mẫu'} <ArrowRight size={16} aria-hidden="true" /></Link>
          <p className={styles.demoNote}>Chỉ dùng dữ liệu giả lập. Đây chưa phải biểu mẫu chính thức.</p>
        </section>
        <section className={styles.noteCard}>
          <h3>Hồ sơ của bạn. Bản nháp riêng.</h3>
          <p>Thông tin được lấy từ hồ sơ chỉ là bản sao để điền biểu mẫu. Chỉnh sửa biểu mẫu không tự cập nhật hồ sơ đã lưu.</p>
          <p>Lưu hồ sơ không gửi giấy tờ đến cơ quan tiếp nhận và không xác minh danh tính pháp lý.</p>
        </section>
      </aside>
    </div>
  </>;
}
