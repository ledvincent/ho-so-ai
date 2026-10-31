'use client';
import { useLocale, LocaleToggle } from '@/components/ui/locale';

import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowUp, LogOut, X } from 'lucide-react';
import { flushSync } from 'react-dom';
import { BrandMark } from '@/components/ui/brand';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import { verifySchema } from '@/components/guided-portal/api';
import { GuidedWorkbench } from '@/components/guided-portal/workbench';
import { DossierChecklist } from './dossier';
import { DocumentCards } from './document-cards';
import { sameDocument, type Clarification, type DocumentEvidence, type DocumentPresentation, type FormAction } from './document-model';
import { DiscoveryRequestError } from './api';
import type { GuidedAdapter, Message } from '@/components/guided-portal/state';
import type { PrefillClient } from '@/components/saved-profile/prefill-model';
import shared from '@/components/guided-portal/portal.module.css';
import { acceptsDiscoveryReply, currentCandidate, GREETING, supportedWorkflow, unavailableDiscovery, type Candidate, type Citation, type DiscoveryAdapter, type ProcedureDetail } from './model';
import { fixtureCatalog, fixtureDiscovery, fixtureFormAdapter, type FixtureScenario } from './fixtures';
import styles from './chat.module.css';

export function ProcedureChat({ username, formAdapter, discovery = unavailableDiscovery, profile, logout, onExpired, fixtures = false }: { username: string; formAdapter: GuidedAdapter; discovery?: DiscoveryAdapter; profile?: { client: PrefillClient; session: string }; logout: () => Promise<void>; onExpired: () => void; fixtures?: boolean }) {
  const { t } = useLocale();
  const [messages, setMessages] = useState<(Message & { citations?: Citation[] })[]>([{ role: 'assistant', content: GREETING, ui: true }]);
  const [answer, setAnswer] = useState('');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [catalog, setCatalog] = useState<'idle' | 'no-match' | 'unavailable' | 'unresolved'>('idle');
  const [catalogData, setCatalogData] = useState<{ configured: boolean; indexReady: boolean; procedures: Candidate[] } | null>(null);
  const [retrievalState, setRetrievalState] = useState<string | null>(null);
  const [choices, setChoices] = useState<Clarification[]>([]);
  const [lastQuestion, setLastQuestion] = useState('');
  const [evidence, setEvidence] = useState<DocumentEvidence>({ documents: [], citations: [] });
  const [installed, setInstalled] = useState<FormAction[]>([]);
  const [selectedAction, setSelectedAction] = useState<FormAction | null>(null);
  const [detail, setDetail] = useState<ProcedureDetail | null>(null);
  const [formSha, setFormSha] = useState<string | null>(null);
  const [readOnly, setReadOnly] = useState(false);
  const [confirmedCode, setConfirmedCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [formContext, setFormContext] = useState<{ detail: ProcedureDetail; formSha: string; workflow?: DocumentPresentation } | null>(null);
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
  function clear() { abort(); setMessages([]); setCandidates([]); setCatalog('idle'); setCatalogData(null); setRetrievalState(null); setChoices([]); setLastQuestion(''); setEvidence({ documents: [], citations: [] }); setInstalled([]); setSelectedAction(null); setDetail(null); setFormSha(null); setFormContext(null); setAnswer(''); setReadOnly(false); setConfirmedCode(null); setConfirmReset(false); setFormEpoch(value => value + 1); }
  function reset() { clear(); setMessages([{ role: 'assistant', content: GREETING, ui: true }]); }
  function append(content: string) { setMessages(previous => [...previous, { role: 'assistant', content, ui: true }]); }
  function editAnswer(value: string) {
    abort(); setAnswer(value); setChoices([]);
    if (!confirmedCode) { setCandidates([]); setCatalog('idle'); setDetail(null); setInstalled([]); setSelectedAction(null); setFormSha(null); setFormContext(null); setReadOnly(false); }
  }
  function failed(error: unknown, fallback: string) {
    if (error instanceof Error && error.name === 'SessionExpired') { flushSync(clear); onExpired(); }
    else if (error instanceof DiscoveryRequestError && error.status === 409) { setRetrievalState(null); setChoices([]); append('Ngữ cảnh tra cứu đã hết hạn hoặc thay đổi. Hãy gửi lại nhu cầu để bắt đầu lượt tra cứu mới.'); }
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
  async function submit(event: FormEvent) { event.preventDefault(); await send(answer.trim()); }
  async function loadProcedure(code: string, signal: AbortSignal, candidate?: Candidate) {
    const results = await Promise.allSettled([
      candidate ? adapter.detail(candidate, signal) : adapter.detailCode ? adapter.detailCode(code, signal) : Promise.reject(new Error('Procedure inspection unavailable')),
      adapter.documents ? adapter.documents(code, signal) : Promise.resolve([]),
    ]);
    for (const result of results) if (result.status === 'rejected' && result.reason instanceof Error && result.reason.name === 'SessionExpired') throw result.reason;
    if (results[0].status === 'rejected') throw results[0].reason;
    return { detail: results[0].value, actions: results[1].status === 'fulfilled' ? results[1].value : [] };
  }
  async function send(text: string, choice?: Clarification) {
    if (text.length < 2 || busy || text.length > 1000 || (choice && (!retrievalState || !choices.some(item => item.id === choice.id)))) return;
    abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller;
    setBusy(true); setAnswer(''); setChoices([]); setCatalog('idle');
    if (!confirmedCode) { setCandidates([]); setDetail(null); setInstalled([]); setSelectedAction(null); setFormSha(null); setReadOnly(false); }
    setMessages(previous => [...previous, { role: 'user', content: choice?.label ?? text }]);
    try {
      const history = messages.filter(item => item.content.trim().length > 0 && item.content.trim().length <= 16000).slice(-12).map(({ role, content }) => ({ role, content }));
      // Producer clarification owns routing; flat search cannot bypass its ambiguity.
      const chat = await adapter.chat(text, history, choice ? null : confirmedCode, controller.signal, { retrievalState, ...(choice ? { clarificationAnswer: choice.id } : {}) });
      if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
      setMessages(previous => [...previous, { role: 'assistant', content: chat.answer, ui: chat.ui, citations: chat.citations }]);
      setRetrievalState(chat.retrievalState ?? null); setChoices(chat.choices ?? []); setLastQuestion(text);
      setEvidence({ documents: chat.documents ?? [], citations: chat.citations });
      if (chat.choices?.length) return;
      if (chat.procedureCode && !confirmedCode && adapter.detailCode) {
        const inspected = await loadProcedure(chat.procedureCode, controller.signal);
        if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
        setCandidates([inspected.detail.candidate]); setDetail(inspected.detail); setInstalled(inspected.actions);
      } else if (!confirmedCode && fixtures) {
        const found = await adapter.search(text, controller.signal);
        if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
        setCandidates(found.candidates); if (!found.candidates.length) setCatalog('no-match');
      } else if (!chat.procedureCode && !confirmedCode) {
        setCatalog('unresolved');
      }
    } catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) { setCatalog('unavailable'); failed(error, 'Tra cứu thủ tục hiện chưa khả dụng. Mình chưa thể xác định thủ tục phù hợp và chưa chọn biểu mẫu nào. Bạn vẫn có thể nhập lại nhu cầu hoặc thử lại sau.'); if (!choice) setAnswer(text); } }
    finally { if (attempt === generation.current) setBusy(false); }
  }
  async function browseCatalog() {
    if (!adapter.setup || busy) return;
    abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller; setBusy(true);
    try { const data = await adapter.setup(controller.signal); if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return; setCatalogData(data); setCandidates(data.procedures); setChoices([]); }
    catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) failed(error, 'Chưa tải được danh mục từ dịch vụ cung cấp dữ liệu.'); }
    finally { if (attempt === generation.current) setBusy(false); }
  }
  async function inspect(candidate: Candidate) {
    if (!currentCandidate(candidates, candidate)) return;
    abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller;
    setBusy(true); setDetail(null); setFormSha(null); setFormContext(null); setReadOnly(false);
    try {
      const result = await loadProcedure(candidate.code, controller.signal, candidate);
      if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
      if (result.detail.candidate.code !== candidate.code || result.detail.candidate.name !== candidate.name) throw new Error('ProcedureMismatch');
      setRetrievalState(null); setChoices([]); setSelectedAction(null); setEvidence({ documents: [], citations: [] }); setDetail(result.detail); setInstalled(result.actions);
    } catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) failed(error, 'Chưa tải được thông tin xác nhận cho thủ tục này. Chưa mở biểu mẫu.'); }
    finally { if (attempt === generation.current) setBusy(false); }
  }
  async function inspectAction(action: FormAction) {
    if (!adapter.detailCode || busy || choices.length) return;
    abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller; setBusy(true);
    try {
      const result = await loadProcedure(action.procedure_code, controller.signal);
      if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
      const match = result.actions.find(item => sameDocument(item, action));
      if (!match) throw new Error('Document changed');
      setCandidates([result.detail.candidate]); setDetail(result.detail); setInstalled(result.actions); setSelectedAction(match); setFormSha(match.template_sha256); setReadOnly(false);
    } catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) failed(error, 'Tài liệu đã thay đổi hoặc chưa có quy trình điền. Hãy kiểm tra lại phiên bản nguồn.'); }
    finally { if (attempt === generation.current) setBusy(false); }
  }
  async function confirm() {
    if (!detail || !currentCandidate(candidates, detail.candidate)) return;
    if (!fixtures && selectedAction && adapter.document) {
      if (!installed.some(item => sameDocument(item, selectedAction)) || selectedAction.procedure_code !== detail.candidate.code) return;
      abort(); const attempt = generation.current; const controller = new AbortController(); request.current = controller; setBusy(true);
      try {
        const workflow = await adapter.document(selectedAction, controller.signal);
        if (!acceptsDiscoveryReply(attempt, generation.current, controller.signal)) return;
        setFormContext({ detail, formSha: workflow.action.template_sha256, workflow }); setFormEpoch(value => value + 1);
      } catch (error) { if (acceptsDiscoveryReply(attempt, generation.current, controller.signal)) failed(error, 'Chưa thể mở quy trình điền đúng phiên bản cho thủ tục đã chọn. Thông tin lựa chọn vẫn được giữ; chưa tạo bản nháp.'); }
      finally { if (attempt === generation.current) setBusy(false); }
      return;
    }
    if (!fixtures) { setReadOnly(true); setConfirmedCode(detail.candidate.code); append('Đã xác nhận thủ tục để hỏi đáp. Chưa chọn quy trình điền cho tài liệu.'); return; }
    if (detail.forms.length > 0 && !formSha) return;
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
  const documentBinding = formContext ? `${formContext.detail.candidate.code}:${formContext.formSha}:${formContext.workflow?.action.document_id ?? "legacy"}:${formContext.workflow?.action.template_version ?? "legacy"}:${formEpoch}` : "";
  if (logoutFailed) return <main className={shared.loginPage}><section className={shared.loginCard}><h1>{t("Chưa xác nhận được đăng xuất.")}</h1><p>{t("Nội dung đã được đóng trên màn hình này.")}</p><button className={shared.primary} onClick={leave}>{t("Thử lại")}</button></section></main>;
  if (formContext && (formContext.workflow || supportedWorkflow(formContext.detail, formContext.formSha))) return <><GuidedWorkbench key={formEpoch} username={username} workflow={formContext.workflow} adapter={formContext.workflow && formContext.workflow.action.document_id !== "na5-provincial-stay-extension" ? null : activeFormAdapter} logout={logout} onExpired={onExpired} prefill={profile && !formContext.workflow ? { client: profile.client, context: { session: profile.session, document: documentBinding, procedureCode: formContext.detail.candidate.code, formSha: formContext.formSha, schemaVersion: '50fe2f675df97308aeafef25c791eada67ea857170c332f3aacd38d28fd3d5c3' } } : undefined} procedureQA={{ client: adapter, code: formContext.detail.candidate.code }} dossier={formContext.detail} introMessages={[...messages, { role: 'assistant', ui: true, content: `Bạn đã xác nhận ${formContext.detail.candidate.name} (${formContext.detail.candidate.code}).` }]} onNewProcedure={() => setConfirmReset(true)} contextNotice={fixtures ? t("Tình huống thử giao diện · lựa chọn thủ tục là dữ liệu giả lập, không phải kết quả tra cứu.") : undefined} />{confirmReset && <div className={shared.modalBackdrop}><section className={shared.review} role="dialog" aria-modal="true" aria-labelledby="reset-title"><h2 id="reset-title">{t("Bắt đầu thủ tục khác?")}</h2><p>{t("Bản nháp và cuộc trò chuyện hiện tại sẽ bị xóa khỏi phiên này. Hồ sơ đã lưu không thay đổi.")}</p><button className={shared.primary} type="button" onClick={reset}>{t("Xóa bản nháp và bắt đầu lại")}</button><button className={styles.cancel} type="button" onClick={() => setConfirmReset(false)}>{t("Giữ bản nháp hiện tại")}</button></section></div>}</>;
  return <main id="main-content" className={shared.app} style={viewportStyle}>
    <header className={shared.topbar}><div className={shared.logo}><BrandMark /><span>{t("Hồ Sơ ")}<b>{t("AI")}</b></span></div><LocaleToggle compact /><nav aria-label={t("Không gian cá nhân")}><Link href="/portal" prefetch={false}>{t("Hồ sơ")}</Link>{messages.length > 1 && <button type="button" onClick={reset}>{t("Bắt đầu lại")}</button>}</nav><button type="button" onClick={leave} className={shared.logout} aria-label={t("Đăng xuất")}><span>{username}</span><LogOut size={16} /></button></header>
    <div className={`${shared.content} ${styles.content}`}>
      {fixtures && <div className={styles.fixtureNotice}><b>{t("Kiểm thử giao diện · Dữ liệu giả lập")}</b><p>{t("Không gọi tìm kiếm hay mô hình. Kết quả dưới đây là tình huống thử được chọn thủ công.")}</p><label htmlFor="discovery-scenario">{t("Tình huống")}</label><select id="discovery-scenario" value={scenario} onChange={event => { reset(); setScenario(event.target.value as FixtureScenario); }}><option value="ambiguous_visa">{t("Thị thực · cần phân biệt kết quả")}</option><option value="stay_extension">{t("Gia hạn tạm trú · mẫu được hỗ trợ")}</option><option value="no_match">{t("Không có kết quả")}</option><option value="unavailable">{t("Dịch vụ không khả dụng")}</option></select></div>}
      <section className={`${shared.conversation} ${styles.conversation}`} aria-label={t("Trò chuyện về thủ tục")} aria-live="polite"><div className={shared.thread}>
        {messages.length === 1 ? <div className={styles.welcome}><BrandMark /><h1>{t(GREETING)}</h1><p>{t("Hãy mô tả nhu cầu của bạn. Chọn đúng thủ tục trước khi chuẩn bị biểu mẫu.")}</p></div> : messages.map((message, index) => <article key={index} className={message.role === 'user' ? shared.userMessage : shared.assistantMessage}>{message.role === 'assistant' && <BrandMark />}<div><p>{message.ui ? t(message.content) : message.content}</p>{message.citations?.map(citation => <a key={citation.id} className={styles.citation} href={citation.url} target="_blank" rel="noopener">{citation.title} {t(" ↗")}</a>)}</div></article>)}
        {choices.length > 0 && <section className={styles.clarification} aria-label={t("Làm rõ nhu cầu")}><p>{t("Chọn câu trả lời phù hợp; chưa có thủ tục hoặc biểu mẫu nào được xác nhận.")}</p>{choices.map(choice => <button type="button" key={choice.id} disabled={busy} onClick={() => { void send(lastQuestion, choice); }}>{choice.label}</button>)}</section>}<DocumentCards evidence={evidence} onOpen={choices.length ? undefined : inspectAction} busy={busy} />{candidates.length > 0 && <div className={styles.candidates} aria-label={t("Thủ tục tìm được")}>{candidates.map(candidate => <article key={candidate.code}><span>{fixtures ? t("Tình huống giả lập") : catalogData ? t("Danh mục từ dịch vụ cung cấp dữ liệu") : t("Kết quả tìm kiếm")} {t(" · ")}{candidate.code}</span><h2>{candidate.name}</h2><button type="button" disabled={busy} onClick={() => inspect(candidate)}>{t("Xem và xác nhận")}</button></article>)}</div>}
        {catalog !== 'idle' && <section className={styles.catalog} aria-label={t("Danh mục thủ tục")}><h2>{catalog === 'no-match' ? t("Chưa có kết quả khớp với nhu cầu") : catalog === 'unresolved' ? t("Chưa xác nhận thủ tục phù hợp") : t("Chưa kiểm tra được kết quả tìm kiếm")}</h2><p>{catalogData ? t("Danh sách bên trên do dịch vụ cung cấp dữ liệu trả về. Chọn và kiểm tra thủ tục trước khi xác nhận.") : t("Bạn có thể xem danh mục từ dịch vụ cung cấp dữ liệu. Danh sách chưa được tải không xác nhận có thủ tục phù hợp.")}</p>{catalogData && <p>{t("Chỉ mục tra cứu:")} {catalogData.indexReady ? t("Sẵn sàng") : t("Chưa sẵn sàng")} · {t("Dịch vụ trả lời:")} {catalogData.configured ? t("Đã cấu hình") : t("Chưa cấu hình")}</p>}{!fixtures && <button type="button" disabled={busy || !adapter.setup} onClick={() => { void browseCatalog(); }}>{t("Xem danh mục thủ tục")}</button>}{fixtures && <><p>{t("Danh sách dưới đây chỉ dành cho tình huống UI, không xác nhận dịch vụ đang có các thủ tục này.")}</p><button type="button" onClick={() => { setCandidates(fixtureCatalog); setCatalog('idle'); }}>{t("Xem danh mục giả lập")}</button></>}</section>}
        {detail && <section className={styles.detail} aria-label={t("Xác nhận thủ tục")}><div><span>{readOnly ? t("CHỈ XEM") : t("CHƯA CHỌN BIỂU MẪU")}</span><button type="button" aria-label={t("Đóng thông tin thủ tục")} onClick={() => { abort(); setDetail(null); setFormSha(null); setFormContext(null); setReadOnly(false); }}><X size={16} /></button></div><h2>{detail.candidate.name}</h2><p>{t("Mã thủ tục: ")}<b>{detail.candidate.code}</b></p>{detail.provenance.map((item, index) => <p key={index} className={styles.provenance}>{t(item)}</p>)}{installed.map(action => <div className={styles.formReference} key={action.document_id + action.template_version}><label><input type="radio" name="installed-document" disabled={readOnly || busy} checked={selectedAction?.document_id === action.document_id && selectedAction?.template_version === action.template_version} onChange={() => { setSelectedAction(action); setFormSha(action.template_sha256); }} />{action.form_id} · {action.revision}</label><p>{action.review_status} · {action.applicability}</p><details><summary>{t("Chi tiết tài liệu nguồn")}</summary><small>{action.document_id}<br />{action.template_version}<br />{action.template_sha256}</small></details></div>)}{detail.forms.map(form => <div key={form.sha256} className={styles.formReference}><label><input type="radio" name="confirmed-form" checked={formSha === form.sha256} disabled={!fixtures || readOnly || busy} onChange={() => setFormSha(form.sha256)} />{form.label}</label><small>{t("SHA-256: ")}{form.sha256}</small>{form.href && <a href={form.href} target="_blank" rel="noopener">{t("Xem tài liệu gốc ↗")}</a>}</div>)}{!readOnly && <button className={shared.primary} type="button" disabled={busy || (fixtures && detail.forms.length > 0 && !formSha)} onClick={confirm}>{selectedAction || supportedWorkflow(detail, formSha) ? t("Xác nhận thủ tục và mở bản nháp") : t("Xác nhận thủ tục · chỉ xem")}</button>}{readOnly && <><p>{t("Chưa có quy trình điền tương thích. Bạn có thể tiếp tục tra cứu trong cuộc trò chuyện.")}</p><DossierChecklist detail={detail} /></>}</section>}
        {busy && <p className={shared.thinking} role="status">{t("Đang kiểm tra thông tin thủ tục…")}</p>}<div ref={tail} />
      </div></section>
      <form className={shared.composerArea} onSubmit={submit}><div className={shared.composer}><label className={shared.srOnly} htmlFor="procedure-message">{t("Bạn cần hỗ trợ gì?")}</label><textarea id="procedure-message" rows={1} maxLength={1000} value={answer} onChange={event => editAnswer(event.target.value)} placeholder={t("Ví dụ: Tôi cần xin thị thực mới…")} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><button type="submit" aria-label={t("Gửi nhu cầu")} disabled={busy || answer.trim().length < 2}><ArrowUp size={19} /></button></div><p className={shared.composerNote}>{t("Thông tin cần có nguồn để đối chiếu. Biểu mẫu chỉ mở sau khi bạn xác nhận thủ tục.")}</p></form>
    </div>
  </main>;
}
