'use client';
import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowUp, Check, LogOut, RotateCcw, X } from 'lucide-react';
import { flushSync } from 'react-dom';
import { BrandMark } from '@/components/ui/brand';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import { activeFields, captureReview, emptyValues, issues, updateValue, type Review, type Values } from '@/components/na5-demo/model';
import { GuidedDocument } from './document';
import { parts } from './document-layout';
import { checkedValues, changesBetween, fieldLabel, nextMissing, type Change, type GuidedAdapter, type Message } from './state';
import styles from './portal.module.css';

const firstQuestion = 'Chào bạn! Mình sẽ cùng bạn chuẩn bị tờ khai gia hạn tạm trú, từng câu hỏi một. Họ tên đầy đủ trên hộ chiếu của bạn là gì?';
type Entry = Message & { changes?: Change[] };

export function GuidedWorkbench({ username, adapter, logout, onExpired, provisional = false }: { username: string; adapter: GuidedAdapter | null; logout: () => Promise<void>; onExpired: () => void; provisional?: boolean }) {
  const [values, setValues] = useState<Values>(emptyValues);
  const [revision, setRevision] = useState(1);
  const [activeId, setActiveId] = useState<string | null>('applicant_full_name');
  const [messages, setMessages] = useState<Entry[]>([{ role: 'assistant', content: firstQuestion }]);
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [logoutFailed, setLogoutFailed] = useState(false);
  const [undoValues, setUndoValues] = useState<Values | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [review, setReview] = useState<Review | null>(null);
  const [ack, setAck] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const [viewportStyle, setViewportStyle] = useState<CSSProperties>({});
  const current = useRef({ revision: 1, generation: 0 });
  const request = useRef<AbortController | null>(null);
  const tail = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);

  function invalidate() { current.current.revision += 1; current.current.generation += 1; request.current?.abort(); setRevision(current.current.revision); setBusy(false); setReview(null); setAck(false); }
  function clear() { invalidate(); setValues(emptyValues()); setUndoValues(null); setMessages([]); setAnswer(''); setError(''); setReviewOpen(false); }
  useEffect(() => {
    const cleanup = listenForProfilePageLifecycle(window, () => { flushSync(clear); onExpired(); }, () => {});
    return () => { cleanup(); current.current.generation += 1; request.current?.abort(); };
  }, []);
  useEffect(() => { tail.current?.scrollIntoView({ block: 'end' }); }, [messages, busy, error]);
  useEffect(() => {
    const viewport = window.visualViewport;
    const resize = () => setViewportStyle(viewport ? { height: viewport.height, top: viewport.offsetTop } : {});
    resize(); viewport?.addEventListener('resize', resize); viewport?.addEventListener('scroll', resize);
    return () => { viewport?.removeEventListener('resize', resize); viewport?.removeEventListener('scroll', resize); };
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); const text = answer.trim(); if (!text || busy) return;
    if (!adapter) { setError('Dịch vụ hội thoại đang chờ kết nối. Chưa có mục nào được thay đổi.'); return; }
    const baseRevision = current.current.revision; const attempt = ++current.current.generation;
    const controller = new AbortController(); request.current = controller;
    const history: Message[] = [...messages.map(({ role, content }) => ({ role, content })), { role: 'user', content: text }];
    setMessages(history); setAnswer(''); setError(''); setBusy(true);
    try {
      const response = await adapter({ message: text, values: { ...values }, revision: baseRevision, focusField: activeId, history, signal: controller.signal });
      if (attempt !== current.current.generation || baseRevision !== current.current.revision || controller.signal.aborted) return;
      const next = checkedValues(response.values); const changes = changesBetween(values, next);
      if (changes.length) { setUndoValues({ ...values }); setValues(next); current.current.revision += 1; setRevision(current.current.revision); setReview(null); setAck(false); }
      setActiveId(response.nextField ?? nextMissing(next)?.id ?? null);
      setMessages(previous => [...previous, { role: 'assistant', content: response.answer, changes }]);
    } catch (failure) {
      if (attempt !== current.current.generation || controller.signal.aborted) return;
      if (failure instanceof Error && failure.name === 'SessionExpired') { flushSync(clear); onExpired(); return; }
      setError('Trợ lý chưa thể trả lời. Bản nháp hiện tại được giữ lại. Hãy thử lại.'); setAnswer(text);
    } finally { if (attempt === current.current.generation) setBusy(false); }
  }
  function manualEdit(id: string, value: string) {
    const next = updateValue(values, id, value); invalidate(); setUndoValues({ ...values }); setValues(next); setActiveId(id); setError('');
    setMessages(previous => [...previous, { role: 'assistant', content: 'Đã áp dụng chỉnh sửa của bạn vào cùng bản nháp.', changes: changesBetween(values, next) }]);
  }
  function undo() { if (!undoValues) return; invalidate(); const restored = undoValues; setValues(restored); setUndoValues(null); setActiveId(nextMissing(restored)?.id ?? null); setMessages(previous => [...previous, { role: 'assistant', content: 'Đã hoàn tác thay đổi cuối cùng và khôi phục bản nháp trước đó.' }]); }
  async function leave() { flushSync(clear); try { await logout(); onExpired(); } catch { setLogoutFailed(true); } }
  const validation = issues(values);
  for (const field of activeFields(values)) if (parts(field, values[field.id] ?? '').some(part => part.overflow)) validation[field.id] = 'Nội dung chưa vừa vùng điền.';
  const remaining = Object.keys(validation).length;
  if (logoutFailed) return <main className={styles.loginPage}><section className={styles.loginCard}><BrandMark /><h1>Chưa xác nhận được đăng xuất.</h1><p>Bản nháp đã được xóa khỏi màn hình. Hãy thử lại để kết thúc phiên trên máy chủ.</p><button type="button" className={styles.primary} onClick={leave}>Thử đăng xuất lại</button></section></main>;
  return <main id="main-content" className={`${styles.app} ${manualMode ? styles.manualMode : ''}`} style={viewportStyle}>
    <header className={styles.topbar}><div className={styles.logo}><BrandMark /><span>Hồ Sơ <b>AI</b></span></div><nav aria-label="Không gian cá nhân"><Link href="/research" prefetch={false}>Tra cứu</Link><Link href="/portal" prefetch={false}>Hồ sơ</Link><button type="button" onClick={() => setReviewOpen(true)}>Tài liệu</button></nav><button type="button" onClick={leave} className={styles.logout} aria-label="Đăng xuất"><span>{username}</span><LogOut size={16} /></button></header>
    <div className={styles.content}><div className={styles.procedure}><div><h1>Gia hạn tạm trú</h1><p>NA5 · Cấp tỉnh · 1.001146</p></div><button type="button" onClick={() => setReviewOpen(true)}>{remaining ? `${remaining} mục cần bổ sung` : 'Rà soát bản nháp'}</button></div>
      {provisional && <p className={styles.provisional}>Bản xem UI tạm thời · chưa kết nối đăng nhập và mô hình · chỉ dùng dữ liệu giả</p>}
      <GuidedDocument values={values} activeId={activeId} onEdit={manualEdit} onManualMode={setManualMode} />
      <section className={styles.conversation} aria-label="Trò chuyện với trợ lý" aria-live="polite"><div className={styles.thread}>{messages.map((message, index) => <article key={index} className={message.role === 'user' ? styles.userMessage : styles.assistantMessage}>{message.role === 'assistant' && <BrandMark />}<div><p>{message.content}</p>{Boolean(message.changes?.length) && <details className={styles.changes}><summary><Check size={12} />{message.changes!.length} thay đổi trên bản nháp</summary>{message.changes!.map(change => <p key={change.id}><b>{fieldLabel(change.id)}</b><span>{change.before || 'Trống'} → {change.after || 'Đã xóa'}</span></p>)}</details>}</div></article>)}{busy && <p className={styles.thinking} role="status">Trợ lý đang chuẩn bị câu hỏi tiếp theo…</p>}{error && <p className={styles.error} role="alert">{error}</p>}<div ref={tail} /></div></section>
      <div className={styles.composerArea}>{undoValues && <button type="button" className={styles.undo} onClick={undo}><RotateCcw size={12} />Hoàn tác thay đổi cuối</button>}<form className={styles.composer} onSubmit={submit}><label className={styles.srOnly} htmlFor="guided-answer">Câu trả lời của bạn</label><textarea id="guided-answer" ref={composer} value={answer} onChange={event => setAnswer(event.target.value)} placeholder="Trả lời theo cách của bạn…" rows={1} maxLength={4000} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><button type="submit" aria-label="Gửi" disabled={busy || !answer.trim()}><ArrowUp size={19} /></button></form><p className={styles.composerNote}>Kiểm tra thông tin được đề xuất. Hồ sơ không được lưu tự động.</p></div>
    </div>
    {reviewOpen && <div className={styles.modalBackdrop}><section className={styles.review} role="dialog" aria-modal="true" aria-labelledby="review-title"><header><h2 id="review-title">Rà soát tài liệu NA5</h2><button type="button" aria-label="Đóng rà soát" onClick={() => setReviewOpen(false)}><X size={20} /></button></header><p>Mẫu đang chờ người duyệt. Chức năng tải biểu mẫu đã điền đang khóa.</p>{remaining > 0 ? <p>{remaining} mục cần kiểm tra.</p> : <button type="button" className={styles.primary} onClick={() => { setReview(captureReview(values, revision)); setAck(false); }}>Chốt phiên bản này để rà soát</button>}<dl>{Object.entries(review?.revision === revision ? review.values : values).map(([id, value]) => value && <div key={id}><dt>{fieldLabel(id)}</dt><dd>{value}</dd></div>)}</dl>{review?.revision === revision && <label className={styles.ack}><input type="checkbox" checked={ack} onChange={event => setAck(event.target.checked)} />Tôi đã kiểm tra phiên bản này.</label>}<button type="button" disabled>Tải xuống · Chờ duyệt mẫu</button><small>Mọi chỉnh sửa đều hủy lần rà soát trước. Không tạo mã xác nhận giả.</small></section></div>}
  </main>;
}
