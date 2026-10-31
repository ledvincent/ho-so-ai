'use client';
import { useLocale, LocaleToggle } from '@/components/ui/locale';

import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import Link from 'next/link';
import { ArrowUp, Check, LogOut, RotateCcw, X } from 'lucide-react';
import { flushSync } from 'react-dom';
import { BrandMark } from '@/components/ui/brand';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import { activeFields, captureReview, emptyValues, issues, payloadValues, updateValue, schema as defaultSchema, type Review, type Values } from '@/components/na5-demo/model';
import type { Clarification, DocumentEvidence, DocumentPresentation, DocumentValidation } from '@/components/procedure-chat/document-model';
import { DocumentCards } from '@/components/procedure-chat/document-cards';
import { DiscoveryRequestError } from '@/components/procedure-chat/api';
import { GuidedDocument } from './document';
import { parts } from './document-layout';
import { ConsentedPrefill } from '@/components/saved-profile/prefill';
import type { PrefillClient, PrefillContext } from '@/components/saved-profile/prefill-model';
import type { Citation, DiscoveryAdapter, ProcedureDetail } from '@/components/procedure-chat/model';
import { DossierChecklist } from '@/components/procedure-chat/dossier';
import { appendUserTurn, checkedValues, changesBetween, fieldLabel, nextMissing, type Change, type GuidedAdapter, type GuidedReply, type Message } from './state';
import styles from './portal.module.css';

const firstQuestion = 'Chào bạn! Mình sẽ cùng bạn chuẩn bị tờ khai gia hạn tạm trú, từng câu hỏi một. Họ tên đầy đủ trên hộ chiếu của bạn là gì?';
type Entry = Message & { changes?: Change[]; citations?: Citation[] };

export function GuidedWorkbench({ username, adapter, logout, onExpired, provisional = false, initialGuidance, introMessages = [], onNewProcedure, contextNotice, prefill, procedureQA, dossier, workflow }: { username: string; adapter: GuidedAdapter | null; logout: () => Promise<void>; onExpired: () => void; provisional?: boolean; initialGuidance?: GuidedReply; introMessages?: Message[]; onNewProcedure?: () => void; contextNotice?: string; prefill?: { client: PrefillClient; context: Omit<PrefillContext, 'draftRevision'> }; procedureQA?: { client: DiscoveryAdapter; code: string; initialState?: string | null; history?: Message[]; evidence?: DocumentEvidence }; dossier?: ProcedureDetail; workflow?: DocumentPresentation }) {
  const { t } = useLocale();
  const schema = workflow?.schema ?? defaultSchema;
  const formId = workflow?.action.form_id ?? 'NA5';
  const initialMissing = nextMissing(emptyValues(schema), schema);
  const [values, setValues] = useState<Values>(() => emptyValues(schema));
  const [revision, setRevision] = useState(1);
  const [activeId, setActiveId] = useState<string | null>(initialGuidance?.nextField ?? initialMissing?.id ?? null);
  const [messages, setMessages] = useState<Entry[]>(prefill ? introMessages : [...introMessages, { role: 'assistant', content: initialGuidance?.answer ?? (workflow ? initialMissing ? `Mục tiếp theo: ${initialMissing.label}. Bạn vui lòng bổ sung thông tin này.` : 'Bạn có thể điền các mục tùy chọn bằng trình sửa trực tiếp rồi rà soát bản nháp.' : firstQuestion), ui: initialGuidance ? initialGuidance.ui : true }]);
  const [prefillOpen, setPrefillOpen] = useState(Boolean(prefill));
  const [procedureMessages, setProcedureMessages] = useState<(Message & { citations?: Citation[] })[]>(procedureQA?.history ?? []);
  const [qaState, setQAState] = useState<string | null>(procedureQA?.initialState ?? null);
  const [qaChoices, setQAChoices] = useState<Clarification[]>([]);
  const [qaQuestion, setQAQuestion] = useState('');
  const [qaEvidence, setQAEvidence] = useState<DocumentEvidence>(procedureQA?.evidence ?? { documents: [], citations: [] });
  const [stream, setStream] = useState<'form' | 'procedure'>('form');
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<'form' | 'procedure' | 'choose'>(procedureQA ? 'choose' : 'form');
  const [error, setError] = useState('');
  const [logoutFailed, setLogoutFailed] = useState(false);
  const [undoValues, setUndoValues] = useState<Values | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [review, setReview] = useState<Review | null>(null);
  const [serverValidation, setServerValidation] = useState<{ revision: number; result: DocumentValidation } | null>(null);
  const [serverPreview, setServerPreview] = useState<{ revision: number; pages: DocumentPresentation['pages'] } | null>(null);
  const [reviewProblem, setReviewProblem] = useState('');
  const [ack, setAck] = useState(false);
  const [manualMode, setManualMode] = useState(false);
  const [viewportStyle, setViewportStyle] = useState<CSSProperties>({});
  const current = useRef({ revision: 1, generation: 0 });
  const valuesRef = useRef(values); valuesRef.current = values;
  const request = useRef<AbortController | null>(null);
  const tail = useRef<HTMLDivElement>(null);
  const prefillAnchor = useRef<HTMLDivElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const composerGeneration = useRef(0);

  function invalidate() { current.current.revision += 1; current.current.generation += 1; request.current?.abort(); setRevision(current.current.revision); setBusy(false); setReview(null); setServerValidation(null); setServerPreview(null); setReviewProblem(''); setAck(false); }
  function clear() { invalidate(); valuesRef.current = emptyValues(schema); setValues(emptyValues(schema)); setUndoValues(null); setMessages([]); setProcedureMessages([]); setQAState(null); setQAChoices([]); setQAEvidence({ documents: [], citations: [] }); setPrefillOpen(false); setAnswer(''); setError(''); setReviewOpen(false); }
  function finishPrefill(next: Values, copied: boolean, expectedRevision: number) {
    if (expectedRevision !== current.current.revision) return false;
    const before = valuesRef.current; const changes = changesBetween(before, next);
    if (copied && changes.length) { invalidate(); setUndoValues({ ...before }); valuesRef.current = next; setValues(next); }
    const missing = nextMissing(next, schema); setActiveId(missing?.id ?? null); setPrefillOpen(false); setStream('form');
    setMessages(previous => [...previous, { role: 'assistant', ui: true, content: copied ? 'Đã áp dụng các mục bạn đã chọn vào bản nháp.' : 'Bạn có thể tiếp tục nhập trực tiếp.', changes }, { role: 'assistant', ui: true, content: missing ? `Mục tiếp theo: ${missing.label}. Bạn vui lòng bổ sung thông tin này.` : 'Các mục bắt buộc của NA5 đã được điền. Hãy rà soát bản nháp; thành phần hồ sơ khác vẫn cần kiểm tra riêng.' }]);
    return true;
  }
  useEffect(() => {
    const cleanup = listenForProfilePageLifecycle(window, () => { flushSync(clear); onExpired(); }, () => {});
    return () => { cleanup(); current.current.generation += 1; request.current?.abort(); };
  }, []);
  useEffect(() => { if (prefillOpen) prefillAnchor.current?.scrollIntoView({ block: 'start' }); else tail.current?.scrollIntoView({ block: 'end' }); }, [messages, procedureMessages, stream, busy, error, prefillOpen]);
  useEffect(() => {
    const viewport = window.visualViewport;
    const resize = () => setViewportStyle(viewport ? { height: viewport.height, top: viewport.offsetTop, '--conversation-min': `${viewport.height < 560 ? 70 : Math.min(210, viewport.height * .28)}px` } as CSSProperties : {});
    resize(); viewport?.addEventListener('resize', resize); viewport?.addEventListener('scroll', resize);
    return () => { viewport?.removeEventListener('resize', resize); viewport?.removeEventListener('scroll', resize); };
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); const text = answer.trim(); if (!text || busy || prefillOpen) return;
    if (mode === 'choose') { setError('Đây là câu hỏi về thủ tục hay câu trả lời cho mục đang điền? Chọn một chế độ trước khi gửi.'); return; }
    if (mode === 'procedure') { await askProcedure(text); return; }
    if (text.length > 2000) { setError('Câu trả lời tối đa 2.000 ký tự. Hãy rút gọn trước khi gửi.'); return; }
    if (!adapter) { setError('Dịch vụ hội thoại đang chờ kết nối. Chưa có mục nào được thay đổi.'); return; }
    const baseRevision = current.current.revision; const attempt = ++current.current.generation;
    const submittedComposer = composerGeneration.current;
    const controller = new AbortController(); request.current = controller;
    const history: Message[] = [...messages.map(({ role, content }) => ({ role, content })), { role: 'user', content: text }];
    setMessages(previous => appendUserTurn(previous, text)); setAnswer(''); setError(''); setBusy(true);
    try {
      const response = await adapter({ message: text, values: { ...values }, revision: baseRevision, focusField: activeId, history, signal: controller.signal });
      if (attempt !== current.current.generation || baseRevision !== current.current.revision || controller.signal.aborted) return;
      const next = checkedValues(response.values, schema); const changes = changesBetween(values, next);
      if (changes.length) { setUndoValues({ ...values }); valuesRef.current = next; setValues(next); current.current.revision += 1; setRevision(current.current.revision); setReview(null); setAck(false); }
      setActiveId(response.nextField ?? nextMissing(next, schema)?.id ?? null);
      setMessages(previous => [...previous, { role: 'assistant', content: response.answer, ui: response.ui, changes }]);
    } catch (failure) {
      if (attempt !== current.current.generation || controller.signal.aborted) return;
      if (failure instanceof Error && failure.name === 'SessionExpired') { flushSync(clear); onExpired(); return; }
      setError('Trợ lý chưa thể trả lời. Bản nháp hiện tại được giữ lại. Hãy thử lại.'); if (submittedComposer === composerGeneration.current) setAnswer(text);
    } finally { if (attempt === current.current.generation) { setBusy(false); if (procedureQA) setMode('choose'); } }
  }
  async function askProcedure(text: string, choice?: Clarification) {
    if (!procedureQA) { setError('Hỏi đáp thủ tục chưa được kết nối.'); return; }
    if (choice && (!qaState || !qaChoices.some(item => item.id === choice.id))) return;
    if (text.length < 2 || text.length > 1000) { setError('Câu hỏi thủ tục cần từ 2 đến 1.000 ký tự.'); return; }
    const attempt = ++current.current.generation; const controller = new AbortController(); request.current = controller; setBusy(true); setError(''); setAnswer('');
    const submittedComposer = composerGeneration.current;
    const history = procedureMessages.map(({ role, content }) => ({ role, content }));
    setQAChoices([]);
    setProcedureMessages(previous => [...previous, { role: 'user', content: choice?.label ?? text }]);
    try {
      const response = await procedureQA.client.chat(text, history, choice ? null : procedureQA.code, controller.signal, { retrievalState: qaState, ...(choice ? { clarificationAnswer: choice.id } : {}) });
      if (attempt !== current.current.generation || controller.signal.aborted) return;
      setProcedureMessages(previous => [...previous, { role: 'assistant', content: response.answer, ui: response.ui, citations: response.citations }]);
      if (response.procedureCode && response.procedureCode !== procedureQA.code) {
        setQAState(null); setQAChoices([]); setQAEvidence({ documents: [], citations: [] });
        setError('Câu trả lời đề cập thủ tục khác. Bản nháp hiện tại được giữ nguyên; hãy đổi thủ tục nếu muốn chuẩn bị tài liệu khác.');
      } else {
        setQAState(response.retrievalState ?? null); setQAChoices(response.choices ?? []); setQAQuestion(text);
        setQAEvidence({ documents: response.documents ?? [], citations: response.citations });
      }
    } catch (failure) {
      if (attempt !== current.current.generation || controller.signal.aborted) return;
      if (failure instanceof Error && failure.name === 'SessionExpired') { flushSync(clear); onExpired(); return; }
      if (failure instanceof DiscoveryRequestError && failure.status === 409) { setQAState(null); setQAChoices([]); }
      setError('Hỏi đáp có nguồn chưa khả dụng. Bản nháp và câu trả lời đang điền được giữ nguyên.'); if (submittedComposer === composerGeneration.current) setAnswer(text);
    } finally { if (attempt === current.current.generation) { setBusy(false); setMode('choose'); } }
  }
  function manualEdit(id: string, value: string) {
    const next = updateValue(valuesRef.current, id, value, schema); invalidate(); setUndoValues({ ...valuesRef.current }); valuesRef.current = next; setValues(next); setActiveId(id); setError('');
    setMessages(previous => [...previous, { role: 'assistant', ui: true, content: 'Đã áp dụng chỉnh sửa của bạn vào cùng bản nháp.', changes: changesBetween(values, next) }]);
  }
  function undo() { if (!undoValues) return; invalidate(); const restored = undoValues; valuesRef.current = restored; setValues(restored); setUndoValues(null); setActiveId(nextMissing(restored, schema)?.id ?? null); setMessages(previous => [...previous, { role: 'assistant', ui: true, content: 'Đã hoàn tác thay đổi cuối cùng và khôi phục bản nháp trước đó.' }]); }
  function changeMode(next: 'form' | 'procedure') { current.current.generation += 1; request.current?.abort(); setBusy(false); setError(''); setMode(next); setStream(next); }
  async function checkDocument() {
    if (!workflow || !procedureQA?.client.validateDocument || !procedureQA.client.previewDocument || busy) return;
    const baseRevision = current.current.revision; const attempt = ++current.current.generation;
    const snapshot = payloadValues(valuesRef.current, schema); const controller = new AbortController(); request.current?.abort(); request.current = controller;
    setBusy(true); setReviewProblem(''); setServerPreview(null); setReview(null); setAck(false);
    try {
      const result = await procedureQA.client.validateDocument(workflow, snapshot, controller.signal);
      if (attempt !== current.current.generation || baseRevision !== current.current.revision || controller.signal.aborted) return;
      setServerValidation({ revision: baseRevision, result });
      if (!result.ready) { setActiveId(result.missing[0]?.id ?? null); return; }
      const pages = await procedureQA.client.previewDocument(workflow, snapshot, controller.signal);
      if (attempt !== current.current.generation || baseRevision !== current.current.revision || controller.signal.aborted) return;
      setReview(captureReview(snapshot, baseRevision, schema)); setServerPreview({ revision: baseRevision, pages });
    } catch (failure) {
      if (attempt !== current.current.generation || controller.signal.aborted) return;
      if (failure instanceof Error && failure.name === 'SessionExpired') { flushSync(clear); onExpired(); return; }
      setReviewProblem(failure instanceof DiscoveryRequestError && failure.status === 409 ? 'Phiên bản tài liệu đã thay đổi. Bản nháp được giữ lại; hãy xác nhận lại tài liệu trước khi xem bản kết xuất.' : 'Chưa kiểm tra hoặc kết xuất được bản nháp. Kiểm tra các giá trị và vùng chữ in; hồ sơ đã lưu không thay đổi.');
    } finally { if (attempt === current.current.generation) setBusy(false); }
  }
  async function leave() { flushSync(clear); try { await logout(); onExpired(); } catch { setLogoutFailed(true); } }
  const visibleMessages: Entry[] = stream === 'procedure' ? procedureMessages : messages;
  const validation = issues(values, schema);
  for (const field of activeFields(values, schema)) if (parts(field, values[field.id] ?? '').some(part => part.overflow)) validation[field.id] = 'Nội dung chưa vừa vùng điền.';
  const remaining = Object.keys(validation).length;
  if (logoutFailed) return <main className={styles.loginPage}><section className={styles.loginCard}><BrandMark /><h1>{t("Chưa xác nhận được đăng xuất.")}</h1><p>{t("Bản nháp đã được xóa khỏi màn hình. Hãy thử lại để kết thúc phiên trên máy chủ.")}</p><button type="button" className={styles.primary} onClick={leave}>{t("Thử đăng xuất lại")}</button></section></main>;
  return <main id="main-content" className={`${styles.app} ${manualMode ? styles.manualMode : ''}`} style={viewportStyle}>
    <header className={styles.topbar}><div className={styles.logo}><BrandMark /><span>{t("Hồ Sơ ")}<b>{t("AI")}</b></span></div><LocaleToggle compact /><nav aria-label={t("Không gian cá nhân")}>{onNewProcedure && <button type="button" onClick={onNewProcedure}>{t("Đổi thủ tục")}</button>}<Link href="/portal" prefetch={false}>{t("Hồ sơ")}</Link><button type="button" onClick={() => setReviewOpen(true)}>{t("Rà soát")}</button></nav><button type="button" onClick={leave} className={styles.logout} aria-label={t("Đăng xuất")}><span>{username}</span><LogOut size={16} /></button></header>
    <div className={styles.content}><div className={styles.procedure}><div><h1>{workflow ? workflow.schema.name : t("Gia hạn tạm trú")}</h1><p>{formId} · {schema.procedure_code} · {schema.revision}</p></div><button type="button" onClick={() => setReviewOpen(true)}>{remaining ? t(`${remaining} mục của ${formId} cần bổ sung`) : t("Rà soát bản nháp")}</button></div>
      {provisional && <p className={styles.provisional}>{t("Bản xem UI tạm thời · chưa kết nối đăng nhập và mô hình · chỉ dùng dữ liệu giả")}</p>}
      {contextNotice && <p className={styles.provisional}>{t(contextNotice)}</p>}
      <GuidedDocument workflow={workflow} previewPages={serverPreview?.revision === revision ? serverPreview.pages : undefined} values={values} activeId={activeId} onEdit={manualEdit} onManualMode={setManualMode} />
      <section className={styles.conversation} aria-label={t("Trò chuyện với trợ lý")} aria-live="polite"><div className={styles.thread}>{dossier && <DossierChecklist detail={dossier} />}{stream === 'procedure' && <p className={styles.modeNotice}>{t("Hỏi đáp theo thủ tục ")}{procedureQA?.code}{t(". Câu trả lời nói về thủ tục đã chọn, có thể chưa phù hợp với đúng ấn bản tài liệu đang hiển thị, và không sửa bản nháp. Chỉ dùng dữ liệu giả lập.")}</p>}{visibleMessages.map((message, index) => <article key={index} className={message.role === 'user' ? styles.userMessage : styles.assistantMessage}>{message.role === 'assistant' && <BrandMark />}<div><p>{message.ui ? t(message.content) : message.content}</p>{message.citations?.map(citation => <p key={citation.id}><a href={citation.url} target="_blank" rel="noopener">{citation.title} {t(" ↗")}</a></p>)}{Boolean(message.changes?.length) && <details className={styles.changes}><summary><Check size={12} />{message.changes!.length} {t(" thay đổi trên bản nháp")}</summary>{message.changes!.map(change => <p key={change.id}><b>{t(fieldLabel(change.id, schema))}</b><span>{change.before || t('Trống')} {t(" → ")}{change.after || t('Đã xóa')}</span></p>)}</details>}</div></article>)}{stream === "procedure" && qaChoices.length > 0 && <div aria-label={t("Làm rõ nhu cầu")} className={styles.inputModes}>{qaChoices.map(choice => <button type="button" key={choice.id} disabled={busy} onClick={() => { void askProcedure(qaQuestion, choice); }}>{choice.label}</button>)}</div>}{stream === "procedure" && <DocumentCards evidence={qaEvidence} />}{prefillOpen && prefill && <div ref={prefillAnchor}><ConsentedPrefill client={prefill.client} context={{ ...prefill.context, draftRevision: revision }} draft={values} workflow={schema} onFinish={finishPrefill} onExpired={() => { flushSync(clear); onExpired(); }} /></div>}{busy && <p className={styles.thinking} role="status">{t("Trợ lý đang chuẩn bị câu hỏi tiếp theo…")}</p>}{error && <p className={styles.error} role="alert">{t(error)}</p>}<div ref={tail} /></div></section>
      <div className={styles.composerArea}><div className={styles.inputModes}><button type="button" disabled={prefillOpen} aria-pressed={mode === 'form'} onClick={() => changeMode('form')}>{t("Trả lời mục đang điền")}</button><button type="button" disabled={prefillOpen || !procedureQA} aria-pressed={mode === 'procedure'} onClick={() => changeMode('procedure')}>{t("Hỏi về thủ tục này")}</button></div>{!prefillOpen && mode === 'choose' && <p className={styles.modeNotice}>{t("Chọn “Trả lời mục đang điền” hoặc “Hỏi về thủ tục này” trước khi gửi.")}</p>}{undoValues && <button type="button" className={styles.undo} onClick={undo}><RotateCcw size={12} />{t("Hoàn tác thay đổi cuối")}</button>}<form className={styles.composer} onSubmit={submit}><label className={styles.srOnly} htmlFor="guided-answer">{t("Câu trả lời của bạn")}</label><textarea id="guided-answer" disabled={prefillOpen} ref={composer} value={answer} onChange={event => { composerGeneration.current++; setAnswer(event.target.value); }} placeholder={prefillOpen ? t("Chọn cách dùng hồ sơ ở trên…") : t("Nhập câu hỏi hoặc câu trả lời…")} rows={1} maxLength={2000} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><button type="submit" aria-label={t("Gửi")} disabled={prefillOpen || busy || !answer.trim()}><ArrowUp size={19} /></button></form><p className={styles.composerNote}>{t("Kiểm tra thông tin được đề xuất. Hồ sơ không được lưu tự động.")}</p></div>
    </div>
    {reviewOpen && <div className={styles.modalBackdrop}><section className={styles.review} role="dialog" aria-modal="true" aria-labelledby="review-title"><header><h2 id="review-title">{t("Rà soát")} · {formId}</h2><button type="button" aria-label={t("Đóng rà soát")} onClick={() => setReviewOpen(false)}><X size={20} /></button></header><p>{t("Mẫu đang chờ người duyệt. Chức năng tải biểu mẫu đã điền đang khóa.")}</p>{workflow && <button type="button" className={styles.primary} disabled={busy || !procedureQA?.client.validateDocument} onClick={() => { void checkDocument(); }}>{t(busy ? "Đang kiểm tra tài liệu…" : "Kiểm tra với dịch vụ biểu mẫu")}</button>}{reviewProblem && <p role="alert">{t(reviewProblem)}</p>}{serverValidation?.revision === revision && <div><p>{t(serverValidation.result.ready ? "Các mục bắt buộc đã đủ theo kiểm tra biểu mẫu." : "Bản nháp còn thiếu các mục sau:")}</p><ul>{serverValidation.result.missing.map(item => <li key={item.id}>{t(item.label)}</li>)}</ul><small>{serverValidation.result.note}</small></div>}{serverPreview?.revision === revision && <p role="status">{t("Bản nháp đã được dịch vụ kết xuất. Đóng rà soát để xem đầy đủ các trang.")}</p>}{remaining > 0 ? <p>{remaining} {t(" mục cần kiểm tra.")}</p> : !workflow && <button type="button" className={styles.primary} onClick={() => { setReview(captureReview(values, revision, schema)); setAck(false); }}>{t("Chốt phiên bản này để rà soát")}</button>}<dl>{Object.entries(review?.revision === revision ? review.values : values).map(([id, value]) => value && <div key={id}><dt>{t(fieldLabel(id, schema))}</dt><dd>{value}</dd></div>)}</dl>{review?.revision === revision && <label className={styles.ack}><input type="checkbox" checked={ack} onChange={event => setAck(event.target.checked)} />{t("Tôi đã kiểm tra phiên bản này.")}</label>}<button type="button" disabled>{t("Tải xuống · Chờ duyệt mẫu")}</button><small>{t("Mọi chỉnh sửa đều hủy lần rà soát trước. Không tạo mã xác nhận giả.")}</small></section></div>}
  </main>;
}
