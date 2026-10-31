'use client';
import { useEffect, useState, useSyncExternalStore } from 'react';
import { flushSync } from 'react-dom';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import type { ProfileClient } from './api';
import { RichProfileController, profileProblem } from './editor-state';
import { profileFields } from './fields';
import { ProfileSections } from './sections';
import { PrivacyNote } from './privacy-note';
import styles from './profile.module.css';

export function RichProfileEditor({ client, onExpired, onLogout }: { client: ProfileClient; onExpired: () => void; onLogout: () => Promise<void> }) {
  const [controller] = useState(() => new RichProfileController(client, () => {
    window.dispatchEvent(new Event('hoso-profile-changed'));
    if (typeof BroadcastChannel !== 'undefined') { const channel = new BroadcastChannel('hoso-profile-revision'); channel.postMessage('changed'); channel.close(); }
  }));
  const state = useSyncExternalStore(controller.subscribe, controller.snapshot, controller.snapshot);
  const [confirmReload, setConfirmReload] = useState(false);
  useEffect(() => {
    const stop = listenForProfilePageLifecycle(window, () => flushSync(() => controller.reset()), () => { void controller.load(); });
    void controller.load(); return () => { stop(); controller.reset(); };
  }, [controller]);
  useEffect(() => { if (state.problem === 401) onExpired(); }, [state.problem]);
  const busy = ['idle', 'loading', 'saving'].includes(state.phase);
  const editable = state.phase === 'ready';
  function reload() { if (state.dirty && !confirmReload) { setConfirmReload(true); return; } setConfirmReload(false); void controller.load(); }
  return <>
    <div className={styles.profileToolbar}><span>Thông tin dùng lại · Không bắt buộc</span><button type="button" onClick={() => { controller.reset(); void onLogout(); }}>Đăng xuất</button></div>
    <p className={styles.optional}>Chỉ nhập thông tin bạn muốn lưu. Bạn luôn có thể tiếp tục trò chuyện hoặc nhập tài liệu bằng tay.</p>
    <PrivacyNote />
    {state.phase === 'loading' && <p role="status">Đang tải hồ sơ của bạn…</p>}
    {state.revision === 0 && <p className={styles.optional}>Chưa có hồ sơ đã lưu. Các mục bên dưới có thể để trống.</p>}
    {(state.legacy.nationality || state.legacy.address) && <aside className={styles.legacy}><h2>Thông tin đã lưu trước đây</h2><p>Chỉ xem. Những mục này chưa phân biệt rõ ý nghĩa nên không được tự chuyển sang quốc tịch khi sinh, quốc tịch hiện nay hoặc địa chỉ tạm trú.</p><dl>{state.legacy.nationality && <><dt>Quốc tịch (chung)</dt><dd>{state.legacy.nationality}</dd></>}{state.legacy.address && <><dt>Địa chỉ (chung)</dt><dd>{state.legacy.address}</dd></>}</dl></aside>}
    <ProfileSections fields={profileFields} values={state.values} onEdit={(id, value) => controller.edit(id, value)} onSave={() => { void controller.save(); }} onCancel={() => { controller.cancel(); setConfirmReload(false); }} busy={busy} editable={editable && ![404, 409].includes(state.problem ?? 0)} dirty={state.dirty} problem={state.problem ? profileProblem(state.problem) : undefined} saved={state.saved} />
    <div className={styles.actions}><button type="button" disabled={busy} onClick={reload}>Tải lại hồ sơ</button></div>
    {confirmReload && <div className={styles.problem} role="group" aria-label="Xác nhận tải lại hồ sơ"><p>Tải lại sẽ bỏ các thay đổi chưa lưu trên trang này.</p><div className={styles.actions}><button type="button" onClick={reload}>Bỏ thay đổi và tải lại</button><button type="button" onClick={() => setConfirmReload(false)}>Tiếp tục chỉnh sửa</button></div></div>}
  </>;
}
