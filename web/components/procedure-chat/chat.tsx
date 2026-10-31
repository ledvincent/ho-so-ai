'use client';
import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowUp, LogOut, X } from 'lucide-react';
import { flushSync } from 'react-dom';
import { BrandMark } from '@/components/ui/brand';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import { verifySchema } from '@/components/guided-portal/api';
import { GuidedWorkbench } from '@/components/guided-portal/workbench';
import type { GuidedAdapter, Message } from '@/components/guided-portal/state';
import type { PrefillClient } from '@/components/saved-profile/prefill-model';
import shared from '@/components/guided-portal/portal.module.css';
import { acceptsDiscoveryReply, currentCandidate, GREETING, supportedWorkflow, unavailableDiscovery, type Candidate, type Citation, type DiscoveryAdapter, type ProcedureDetail } from './model';
import { fixtureCatalog, fixtureDiscovery, fixtureFormAdapter, type FixtureScenario } from './fixtures';
import styles from './chat.module.css';

export function ProcedureChat({ username, formAdapter, discovery = unavailableDiscovery, profile, logout, onExpired, fixtures = false }: { username: string; formAdapter: GuidedAdapter; discovery?: DiscoveryAdapter; profile?: { client: PrefillClient; session: string }; logout: () => Promise<void>; onExpired: () => void; fixtures?: boolean }) {
  const [messages, setMessages] = useState<(Message & { citations?: Citation[] })[]>([{ role: 'assistant', content: GREETING }]);
  const [answer, setAnswer] = useState('');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [catalog, setCatalog] = useState<'idle' | 'no-match' | 'unavailable'>('idle');
  const [detail, setDetail] = useState<ProcedureDetail | null>(null);
  const [formSha, setFormSha] = useState<string | null>(null);
  const [readOnly, setReadOnly] = useState(false);
  const [confirmedCode, setConfirmedCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [formContext, setFormContext] = useState<{ detail: ProcedureDetail; formSha: string } | null>(null);
  const [formEpoch, setFormEpoch] = useState(0);
  const [confirmReset, setConfirmReset] = useState(false);
  const [logoutFailed, setLogoutFailed] = useState(false);
  const [scenario, setScenario] = useState<FixtureScenario>('ambiguous_visa');
  const [viewportStyle, setViewportStyle] = useState<CSSProperties>({});
  const request = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const tail = useRef<HTMLDivElement>(null);
  const adapter = useMemo(() => fixtures ? fixtureDiscovery(scenario) : discovery, [fixtures, scenario, discovery]);
  const activeFormAdapter = fixtures ? fixtureFormAdapter : formAdapter;
  function abort() { generation.current += 1; request.current?.abort(); setBusy(false); }
  function clear() { abort(); setMessages([]); setCandidates([]); setCatalog('idle'); setDetail(null); setFormSha(null); setFormContext(null); setAnswer(''); setReadOnly(false); setConfirmedCode(null); setConfirmReset(false); setFormEpoch(value => value + 1); }
  function reset() { clear(); setMessages([{ role: 'assistant', content: GREETING }]); }
  function append(content: string) { setMessages(previous => [...previous, { role: 'assistant', content }]); }
  function editAnswer(value: string) {
    abort(); setAnswer(value);
    if (!confirmedCode) { setCandidates([]); setCatalog('idle'); setDetail(null); setFormSha(null); setFormContext(null); setReadOnly(false); }
  }
  function failed(error: unknown, fallback: string) {
    if (error instanceof Error && error.name === 'SessionExpired') { flushSync(clear); onExpired(); }
    else append(fallback);
  }
  useEffect(() => {
    const stop = listenForProfilePageLifecycle(window, () => { flushSync(clear); onExpired(); }, () => {});
    return () => { stop(); generation.current += 1; request.current?.abort(); };
  }, []);
  useEffect(() => { tail.current?.scrollIntoView({ block: 'end' }); }, [messages, candidates, detail, busy]);
  useEffect(() => {
    const viewport = window.visualViewport; const resize = () => setViewportStyle(viewport ? { height: viewport.height, top: viewport.offsetTop } : {});
    resize(); viewport?.addEventListener('resize', resize); viewport?.addEventListener('scroll', resize);
    return () => { viewport?.removeEventListener('resize', resize); viewport?.removeEventListener('scroll', resize); };
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); const text = answer.trim(); if (text.length < 2 || busy || text.length > 1000) return;
    abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller;
    setBusy(true); setAnswer('');
    if (!confirmedCode) { setCandidates([]); setDetail(null); setFormSha(null); setReadOnly(false); }
    setMessages(previous => [...previous, { role: 'user', content: text }]);
    try {
      const history = messages.filter(item => item.content.trim().length <= 8000).slice(-12).map(({ role, content }) => ({ role, content }));
      const [chat, search] = await Promise.allSettled([
        adapter.chat(text, history, confirmedCode, controller.signal),
        confirmedCode ? Promise.resolve(null) : adapter.search(text, controller.signal),
      ]);
      if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
      for (const result of [chat, search]) if (result.status === 'rejected' && result.reason instanceof Error && result.reason.name === 'SessionExpired') throw result.reason;
      if (chat.status === 'fulfilled') setMessages(previous => [...previous, { role: 'assistant', content: chat.value.answer, citations: chat.value.citations }]);
      else append('Trợ lý tra cứu có nguồn hiện chưa khả dụng. Bạn vẫn có thể nhập lại nhu cầu hoặc thử lại sau.');
      if (search.status === 'fulfilled' && search.value) {
        const result = search.value;
        if (result.status === 'not_found' || !result.candidates.length) { setCatalog('no-match'); append('Chưa tìm thấy thủ tục phù hợp. Bạn có thể mô tả rõ hơn nhu cầu hoặc thử cách diễn đạt khác. Chưa có biểu mẫu nào được chọn.'); }
        else {
          setCandidates(result.candidates);
          append(result.candidates.length > 1 ? 'Có nhiều thủ tục cần phân biệt. Bạn có thể bổ sung chi tiết hoặc xem từng kết quả bên dưới trước khi chọn.' : 'Có một kết quả để bạn xem xét. Hãy kiểm tra tên, mã thủ tục và tài liệu trước khi xác nhận.');
        }
      } else if (!confirmedCode) {
        setCatalog('unavailable');
        append('Tìm kiếm thủ tục chưa khả dụng. Chưa xác định thủ tục phù hợp và chưa chọn biểu mẫu nào.');
      }
    } catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) failed(error, 'Tra cứu thủ tục hiện chưa khả dụng. Mình chưa thể xác định thủ tục phù hợp và chưa chọn biểu mẫu nào. Bạn vẫn có thể nhập lại nhu cầu hoặc thử lại sau.'); }
    finally { if (attempt === generation.current) setBusy(false); }
  }
  async function inspect(candidate: Candidate) {
    if (!currentCandidate(candidates, candidate)) return;
    abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller;
    setBusy(true); setDetail(null); setFormSha(null); setFormContext(null); setReadOnly(false);
    try {
      const result = await adapter.detail(candidate, controller.signal);
      if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
      if (result.candidate.code !== candidate.code || result.candidate.name !== candidate.name) throw new Error('ProcedureMismatch');
      setDetail(result);
    } catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) failed(error, 'Chưa tải được thông tin xác nhận cho thủ tục này. Chưa mở biểu mẫu.'); }
    finally { if (attempt === generation.current) setBusy(false); }
  }
  async function confirm() {
    if (!detail || !currentCandidate(candidates, detail.candidate) || (detail.forms.length > 0 && !formSha)) return;
    if (!supportedWorkflow(detail, formSha)) { setReadOnly(true); setConfirmedCode(detail.candidate.code); append(`Bạn đã chọn ${detail.candidate.name} (${detail.candidate.code}). Hiện chưa có quy trình điền tương thích cho thủ tục này. Thông tin chỉ được mở để xem; không tự chọn biểu mẫu khác.`); return; }
    abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller; setBusy(true);
    try {
      await adapter.verifyWorkflow(detail.candidate, formSha!, controller.signal);
      await verifySchema(controller.signal);
      if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
      setFormContext({ detail, formSha: formSha! }); setFormEpoch(value => value + 1);
    } catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) failed(error, 'Chưa thể mở quy trình điền đúng phiên bản cho thủ tục đã chọn. Thông tin lựa chọn vẫn được giữ; chưa tạo bản nháp.'); }
    finally { if (attempt === generation.current) setBusy(false); }
  }
  async function leave() { flushSync(clear); try { await logout(); onExpired(); } catch { setLogoutFailed(true); } }
  if (logoutFailed) return <main className={shared.loginPage}><section className={shared.loginCard}><h1>Chưa xác nhận được đăng xuất.</h1><p>Nội dung đã được đóng trên màn hình này.</p><button className={shared.primary} onClick={leave}>Thử lại</button></section></main>;
  if (formContext && supportedWorkflow(formContext.detail, formContext.formSha)) return <><GuidedWorkbench key={formEpoch} username={username} adapter={activeFormAdapter} logout={logout} onExpired={onExpired} prefill={profile ? { client: profile.client, context: { session: profile.session, document: `${formContext.detail.candidate.code}:${formContext.formSha}:50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3:${formEpoch}`, procedureCode: formContext.detail.candidate.code, formSha: formContext.formSha, schemaVersion: '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3' } } : undefined} procedureQA={{ client: adapter, code: formContext.detail.candidate.code }} dossier={formContext.detail} introMessages={[...messages, { role: 'assistant', content: `Bạn đã xác nhận ${formContext.detail.candidate.name} (${formContext.detail.candidate.code}).` }]} onNewProcedure={() => setConfirmReset(true)} contextNotice={fixtures ? 'Tình huống thử giao diện · lựa chọn thủ tục là dữ liệu giả lập, không phải kết quả tra cứu.' : undefined} />{confirmReset && <div className={shared.modalBackdrop}><section className={shared.review} role="dialog" aria-modal="true" aria-labelledby="reset-title"><h2 id="reset-title">Bắt đầu thủ tục khác?</h2><p>Bản nháp và cuộc trò chuyện hiện tại sẽ bị xóa khỏi phiên này. Hồ sơ đã lưu không thay đổi.</p><button className={shared.primary} type="button" onClick={reset}>Xóa bản nháp và bắt đầu lại</button><button className={styles.cancel} type="button" onClick={() => setConfirmReset(false)}>Giữ bản nháp hiện tại</button></section></div>}</>;
  return <main id="main-content" className={shared.app} style={viewportStyle}>
    <header className={shared.topbar}><div className={shared.logo}><BrandMark /><span>Hồ Sơ <b>AI</b></span></div><nav aria-label="Không gian cá nhân"><Link href="/portal" prefetch={false}>Hồ sơ</Link>{messages.length > 1 && <button type="button" onClick={reset}>Bắt đầu lại</button>}</nav><button type="button" onClick={leave} className={shared.logout} aria-label="Đăng xuất"><span>{username}</span><LogOut size={16} /></button></header>
    <div className={`${shared.content} ${styles.content}`}>
      {fixtures && <div className={styles.fixtureNotice}><b>Kiểm thử giao diện · Dữ liệu giả lập</b><p>Không gọi tìm kiếm hay mô hình. Kết quả dưới đây là tình huống thử được chọn thủ công.</p><label htmlFor="discovery-scenario">Tình huống</label><select id="discovery-scenario" value={scenario} onChange={event => { reset(); setScenario(event.target.value as FixtureScenario); }}><option value="ambiguous_visa">Thị thực · cần phân biệt kết quả</option><option value="stay_extension">Gia hạn tạm trú · mẫu được hỗ trợ</option><option value="no_match">Không có kết quả</option><option value="unavailable">Dịch vụ không khả dụng</option></select></div>}
      <section className={`${shared.conversation} ${styles.conversation}`} aria-label="Trò chuyện về thủ tục" aria-live="polite"><div className={shared.thread}>
        {messages.length === 1 ? <div className={styles.welcome}><BrandMark /><h1>{GREETING}</h1><p>Hãy mô tả nhu cầu của bạn. Chọn đúng thủ tục trước khi chuẩn bị biểu mẫu.</p></div> : messages.map((message, index) => <article key={index} className={message.role === 'user' ? shared.userMessage : shared.assistantMessage}>{message.role === 'assistant' && <BrandMark />}<div><p>{message.content}</p>{message.citations?.map(citation => <a key={citation.id} className={styles.citation} href={citation.url} target="_blank" rel="noopener">{citation.title} ↗</a>)}</div></article>)}
        {candidates.length > 0 && <div className={styles.candidates} aria-label="Thủ tục tìm được">{candidates.map(candidate => <article key={candidate.code}><span>{fixtures ? 'Tình huống giả lập' : 'Kết quả tìm kiếm'} · {candidate.code}</span><h2>{candidate.name}</h2><button type="button" disabled={busy} onClick={() => inspect(candidate)}>Xem và xác nhận</button></article>)}</div>}
        {catalog !== 'idle' && <section className={styles.catalog} aria-label="Danh mục thủ tục"><h2>{catalog === 'no-match' ? 'Chưa có kết quả khớp với nhu cầu' : 'Chưa kiểm tra được kết quả tìm kiếm'}</h2><p>Danh mục thủ tục từ dịch vụ cung cấp dữ liệu chưa được kết nối. Chưa thể liệt kê các thủ tục đang hỗ trợ. Bạn có thể mô tả rõ hơn nhu cầu hoặc thử lại sau.</p>{fixtures && <><p>Danh sách dưới đây chỉ dành cho tình huống UI, không xác nhận dịch vụ đang có các thủ tục này.</p><button type="button" onClick={() => { setCandidates(fixtureCatalog); setCatalog('idle'); }}>Xem danh mục giả lập</button></>}</section>}
        {detail && <section className={styles.detail} aria-label="Xác nhận thủ tục"><div><span>{readOnly ? 'CHỈ XEM' : 'CHƯA CHỌN BIỂU MẪU'}</span><button type="button" aria-label="Đóng thông tin thủ tục" onClick={() => { abort(); setDetail(null); setFormSha(null); setFormContext(null); setReadOnly(false); }}><X size={16} /></button></div><h2>{detail.candidate.name}</h2><p>Mã thủ tục: <b>{detail.candidate.code}</b></p>{detail.provenance.map((item, index) => <p key={index} className={styles.provenance}>{item}</p>)}{detail.forms.map(form => <div key={form.sha256} className={styles.formReference}><label><input type="radio" name="confirmed-form" checked={formSha === form.sha256} disabled={readOnly || busy} onChange={() => setFormSha(form.sha256)} />{form.label}</label><small>SHA-256: {form.sha256}</small>{form.href && <a href={form.href} target="_blank" rel="noopener">Xem tài liệu gốc ↗</a>}</div>)}{!readOnly && <button className={shared.primary} type="button" disabled={busy || (detail.forms.length > 0 && !formSha)} onClick={confirm}>{supportedWorkflow(detail, formSha) ? 'Xác nhận thủ tục và mở bản nháp' : 'Xác nhận thủ tục · chỉ xem'}</button>}{readOnly && <p>Chưa có quy trình điền tương thích. Bạn có thể tiếp tục tra cứu trong cuộc trò chuyện.</p>}</section>}
        {busy && <p className={shared.thinking} role="status">Đang kiểm tra thông tin thủ tục…</p>}<div ref={tail} />
      </div></section>
      <form className={shared.composerArea} onSubmit={submit}><div className={shared.composer}><label className={shared.srOnly} htmlFor="procedure-message">Bạn cần hỗ trợ gì?</label><textarea id="procedure-message" rows={1} maxLength={1000} value={answer} onChange={event => editAnswer(event.target.value)} placeholder="Ví dụ: Tôi cần xin thị thực mới…" onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><button type="submit" aria-label="Gửi nhu cầu" disabled={busy || answer.trim().length < 2}><ArrowUp size={19} /></button></div><p className={shared.composerNote}>Thông tin cần có nguồn để đối chiếu. Biểu mẫu chỉ mở sau khi bạn xác nhận thủ tục.</p></form>
    </div>
  </main>;
}
