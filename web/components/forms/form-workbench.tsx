'use client';

import { useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import Link from 'next/link';
import { ArrowDownToLine, ArrowLeft, ArrowRight, CircleCheck, FileText, LoaderCircle, PenLine, RefreshCw, ShieldCheck, UserRound } from 'lucide-react';
import { EMPTY_PROFILE, type ProfileFields } from '@/lib/contracts';
import { canDownload, captureRequest, clearDraft, editDraft, isCurrent, newDraft, prefillDraft, validateProfile, type Draft, type FieldId } from '@/lib/forms/draft';
import { readProfile } from '@/components/portal/profile-state';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import { BrandMark } from '@/components/ui/brand';
import { DraftChat } from './draft-chat';
import styles from './form-workbench.module.css';

type Props = { accountState: 'unconfigured' | 'signed-out' | 'signed-in'; accountKey?: string };
const fields: { id: FieldId; label: string; placeholder: string; type?: string; wide?: boolean; hint?: string }[] = [
  { id: 'full_name', label: 'Họ và tên', placeholder: 'Nhập họ tên giả định', wide: true },
  { id: 'date_of_birth', label: 'Ngày sinh', placeholder: '', type: 'date' },
  { id: 'nationality', label: 'Quốc tịch', placeholder: 'Nhập quốc tịch' },
  { id: 'address', label: 'Địa chỉ', placeholder: 'Số nhà, đường, phường và tỉnh/thành phố', wide: true, hint: 'Địa chỉ dài sẽ xuống dòng trong văn bản.' },
  { id: 'phone_number', label: 'Số điện thoại', placeholder: '+84 …', type: 'tel' },
  { id: 'email', label: 'Email', placeholder: 'mau@example.test', type: 'email' },
];
const sample: ProfileFields = { full_name: 'Nguyễn Văn Mẫu', date_of_birth: '1994-05-16', nationality: 'Việt Nam', address: '123 Đường Mẫu, Phường Minh Họa, Thành phố Ví Dụ', phone_number: '+84 000 000 000', email: 'sample@example.test' };

// Translate presentation only; the shared validator and generated limits stay authoritative.
function vietnameseFieldErrors(values: ProfileFields): Partial<Record<FieldId, string>> {
  return Object.fromEntries(Object.entries(validateProfile(values)).map(([field, message]) => {
    const limit = /^Use (\d+) characters or fewer\.$/.exec(message);
    return [field, limit ? `Tối đa ${limit[1]} ký tự.` : message === 'Use a valid date.' ? 'Nhập ngày hợp lệ.' : message === 'Enter a valid email address.' ? 'Nhập địa chỉ email hợp lệ.' : 'Kiểm tra lại thông tin này.'];
  }));
}

export function FormWorkbench({ accountState, accountKey = 'anonymous' }: Props) {
  const [draft, setDraft] = useState<Draft>(newDraft);
  const current = useRef(draft);
  const [preview, setPreview] = useState<string | null>(null);
  const previewUrl = useRef<string | null>(null);
  const [busy, setBusy] = useState<'preview' | 'pdf' | 'profile' | null>(null);
  const [notice, setNotice] = useState('');
  const [failure, setFailure] = useState('');
  const [renderErrors, setRenderErrors] = useState<Partial<Record<FieldId, string>>>({});
  const pending = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const previousAccount = useRef(accountKey);
  const [activeField, setActiveField] = useState<FieldId | null>('full_name');
  const [editingField, setEditingField] = useState<FieldId | null>(null);
  const [changedField, setChangedField] = useState<FieldId | null>(null);
  const [chatEpoch, setChatEpoch] = useState(0);
  const [documentMode, setDocumentMode] = useState<'draft' | 'pdf'>('draft');
  const [expanded, setExpanded] = useState(false);
  const paperArea = useRef<HTMLDivElement | null>(null);
  const fieldNodes = useRef<Partial<Record<FieldId, HTMLDivElement | null>>>({});
  const errors = { ...vietnameseFieldErrors(draft.values), ...renderErrors };
  const valid = Object.keys(errors).length === 0;
  const filled = Object.values(draft.values).filter((value) => value?.trim()).length;
  const missing = fields.filter(field => !draft.values[field.id]?.trim());

  function removePreview() {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null; setPreview(null);
  }
  function update(next: Draft) {
    generation.current += 1; pending.current?.abort(); pending.current = null;
    current.current = next; setDraft(next); removePreview(); setDocumentMode('draft'); setBusy(null); setFailure(''); setNotice(''); setRenderErrors({});
  }
  function replaceDraft(next: Draft) { update(next); setChatEpoch(value => value + 1); setEditingField(null); setActiveField('full_name'); setChangedField(null); }
  function edit(id: FieldId, value: string) { update(editDraft(current.current, id, value)); setChangedField(id); }
  function selectField(id: FieldId) { setActiveField(id); setEditingField(null); setDocumentMode('draft'); }
  useEffect(() => {
    const id = changedField ?? activeField;
    const node = id && fieldNodes.current[id]; const area = paperArea.current;
    if (node && area && documentMode === 'draft') {
      const top = node.getBoundingClientRect().top - area.getBoundingClientRect().top + area.scrollTop - 35;
      if (top < area.scrollTop || top + node.offsetHeight > area.scrollTop + area.clientHeight) area.scrollTo({ top: Math.max(0, top), behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
    }
    if (changedField) { const timer = setTimeout(() => setChangedField(null), 1500); return () => clearTimeout(timer); }
  }, [activeField, changedField, documentMode]);
  useEffect(() => {
    if (previousAccount.current !== accountKey) {
      previousAccount.current = accountKey;
      replaceDraft(clearDraft(current.current));
    }
  }, [accountKey]);
  useEffect(() => {
    const stopLifecycle = listenForProfilePageLifecycle(
      window,
      // Empty the visible inputs before a page-cache snapshot; clear again on restoration.
      () => flushSync(() => replaceDraft(clearDraft(current.current))),
      // Account prefill stays an explicit user action, including after restoration.
      () => {},
    );
    return () => {
      stopLifecycle(); generation.current += 1; pending.current?.abort();
      if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    };
  }, []);

  async function loadAccount() {
    if (accountState !== 'signed-in') return;
    const attempt = ++generation.current; const revision = current.current.revision;
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    setBusy('profile'); setFailure(''); setNotice('');
    try {
      const response = await fetch('/api/profile', { cache: 'no-store', credentials: 'same-origin', redirect: 'error', signal: controller.signal });
      if (attempt !== generation.current || revision !== current.current.revision) return;
      if (!response.ok) {
        if (response.status === 401) {
          replaceDraft(clearDraft(current.current));
          setFailure('Phiên đăng nhập đã kết thúc. Bản nháp đã được xóa trên trang này. Hãy đăng nhập lại để lấy hồ sơ.');
          return;
        }
        setFailure(response.status === 404 ? 'Tài khoản chưa có hồ sơ đã lưu. Bạn có thể nhập dữ liệu giả bằng tay hoặc mở trang hồ sơ.' : 'Chưa thể lấy thông tin đã lưu. Hãy thử lại sau hoặc tiếp tục nhập bằng tay. Các mục đang nhập được giữ nguyên.');
        return;
      }
      const payload: unknown = await response.json();
      if (attempt !== generation.current || revision !== current.current.revision) return;
      const profile = readProfile(payload);
      replaceDraft(prefillDraft(current.current, profile.fields));
      setNotice('Đã sao chép thông tin. Chỉnh sửa ở đây chỉ áp dụng cho biểu mẫu, không thay đổi hồ sơ đã lưu.');
    } catch (error) { if (!(error instanceof DOMException && error.name === 'AbortError') && attempt === generation.current) setFailure('Chưa thể đọc thông tin đã lưu. Các mục đang nhập được giữ nguyên. Hãy thử lại sau.'); }
    finally { if (attempt === generation.current) setBusy(null); }
  }

  async function renderDocument(format: 'preview' | 'pdf') {
    if (!valid || (format === 'pdf' && !canDownload(current.current))) return;
    const snapshot = captureRequest(current.current); const attempt = ++generation.current;
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    if (format === 'preview') {
      removePreview();
      const next = { ...current.current, previewRevision: null, acknowledged: false };
      current.current = next; setDraft(next);
    }
    setBusy(format); setFailure(''); setNotice('');
    try {
      const response = await fetch(`/api/forms/demo/${format}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(snapshot), cache: 'no-store', signal: controller.signal });
      if (attempt !== generation.current || !isCurrent(current.current, snapshot)) return;
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        if (attempt !== generation.current || !isCurrent(current.current, snapshot)) return;
        const code = error.detail?.code ?? error.code;
        const field = error.detail?.field;
        if (typeof field === 'string' && Object.hasOwn(EMPTY_PROFILE, field)) {
          setRenderErrors({ [field]: code === 'text_overflow' ? 'Thông tin quá dài so với vùng điền. Hãy rút gọn; nội dung không bị cắt bớt.' : 'Kiểm tra lại thông tin này trước khi tạo văn bản.' });
        }
        if (response.status === 409) {
          removePreview(); const next = { ...current.current, previewRevision: null, acknowledged: false };
          current.current = next; setDraft(next);
        }
        setFailure(code === 'text_overflow' ? 'Một số thông tin quá dài so với vùng điền. Hãy rút gọn trước khi xem lại; nội dung không bị cắt bớt.' : code === 'unsupported_glyph' ? 'Có ký tự chưa thể hiển thị trong văn bản. Hãy kiểm tra mục được đánh dấu.' : response.status === 404 || response.status === 503 ? 'Chức năng tạo văn bản tạm thời chưa khả dụng. Các mục đang nhập được giữ nguyên; hãy thử lại sau.' : response.status === 409 ? 'Phiên bản biểu mẫu đã thay đổi. Hãy cập nhật bản xem trước và kiểm tra lại.' : 'Chưa thể tạo văn bản. Hãy kiểm tra thông tin rồi thử lại.');
        return;
      }
      const blob = await response.blob();
      if (attempt !== generation.current || !isCurrent(current.current, snapshot)) return;
      if (format === 'preview') {
        removePreview(); const url = URL.createObjectURL(blob); previewUrl.current = url; setPreview(url);
        const next = { ...current.current, previewRevision: snapshot.revision, acknowledged: false };
        current.current = next; setDraft(next); setDocumentMode('pdf'); setExpanded(true); setNotice('Đã cập nhật bản xem PDF. Kiểm tra thông tin trước khi tải xuống.');
      } else {
        const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
        anchor.href = url; anchor.download = 'ho-so-ai-ban-thu-nghiem.pdf'; anchor.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000); setNotice('Đã tải PDF thử nghiệm. Thông tin không được lưu vào hồ sơ tài khoản.');
      }
    } catch (error) { if (!(error instanceof DOMException && error.name === 'AbortError') && attempt === generation.current) setFailure('Chưa thể kết nối dịch vụ tạo văn bản. Các mục đang nhập vẫn được giữ trong thẻ này. Hãy thử lại sau.'); }
    finally { if (attempt === generation.current) setBusy(null); }
  }

  return <main id="main-content" lang="vi" className={styles.main}>
    <div className={styles.heading}><div><h1>Bản nháp của bạn</h1><p>Trả lời trong chat hoặc chạm vào văn bản để sửa.</p></div><span className={styles.draftBadge}>{filled} / 6 mục</span></div>
    <div className={styles.demoNotice}><FileText size={16} aria-hidden="true" /><span><strong>Bản thử nghiệm.</strong> Chỉ dùng dữ liệu giả · Chat theo kịch bản · PDF không dùng để nộp.</span><Link href="/demo/ct01">Thử mẫu CT01 →</Link></div>
    <div className={styles.sourceBar}>
      {accountState === 'signed-in' && <button type="button" onClick={loadAccount} disabled={busy !== null}><UserRound size={15} aria-hidden="true" />{busy === 'profile' ? 'Đang lấy hồ sơ…' : 'Sao chép hồ sơ đã lưu'}</button>}
      <button type="button" onClick={() => replaceDraft({ ...prefillDraft(current.current, sample), source: 'manual' })}>Dùng dữ liệu mẫu</button>
      <button type="button" onClick={() => replaceDraft(clearDraft(current.current))}>Xóa bản nháp</button>
    </div>
    <div className={styles.columns}>
      <section id="document-preview" className={styles.review} aria-labelledby="review-title" aria-busy={busy === 'preview' || busy === 'pdf'}>
        <div className={styles.sectionHeading}><div><h2 id="review-title">Văn bản của bạn</h2><p>{documentMode === 'pdf' ? 'Bản PDF từ dịch vụ tạo văn bản.' : 'Bản nháp cập nhật ngay khi bạn nhập.'}</p></div><button type="button" className={styles.expand} aria-expanded={expanded} onClick={() => setExpanded(value => !value)}>{expanded ? 'Thu gọn' : 'Mở rộng'}</button></div>
        <div className={styles.previewBar}><div><button type="button" aria-pressed={documentMode === 'draft'} onClick={() => setDocumentMode('draft')}>Bản nháp trực tiếp</button><button type="button" aria-pressed={documentMode === 'pdf'} disabled={!preview} onClick={() => setDocumentMode('pdf')}>Bản PDF để rà soát</button></div><span>Thử nghiệm · A4</span></div>
        <div ref={paperArea} className={`${styles.paperArea} ${expanded ? styles.expanded : ''}`}>
          {documentMode === 'pdf' && preview ? <img src={preview} alt="Bản xem PDF thử nghiệm dùng đúng dữ liệu của bản nháp hiện tại." className={styles.document} /> : <div className={styles.livePaper}>
            <BrandMark className={styles.paperLogo} /><p className={styles.paperEyebrow}>BẢN NHÁP THỬ NGHIỆM · KHÔNG DÙNG ĐỂ NỘP</p><h3>Thông tin cá nhân</h3><p className={styles.paperSub}>Chạm vào một mục để chỉnh sửa trực tiếp.</p>
            <div className={styles.paperDivider} />
            {fields.map(field => <div key={field.id} ref={node => { fieldNodes.current[field.id] = node; }} className={`${styles.paperField} ${activeField === field.id ? styles.activeField : ''} ${changedField === field.id ? styles.changedField : ''}`}>
              <label htmlFor={`draft-${field.id}`}>{field.label}{activeField === field.id && <span>Đang điền</span>}</label>
              {editingField === field.id ? <>
                {field.id === 'address' ? <textarea autoFocus id={`draft-${field.id}`} rows={3} value={draft.values[field.id] ?? ''} onChange={event => edit(field.id, event.target.value)} autoComplete="off" aria-invalid={Boolean(errors[field.id])} aria-describedby={`hint-${field.id}`} /> : <input autoFocus id={`draft-${field.id}`} type={field.type ?? 'text'} value={draft.values[field.id] ?? ''} onChange={event => edit(field.id, event.target.value)} autoComplete="off" aria-invalid={Boolean(errors[field.id])} aria-describedby={`hint-${field.id}`} />}
                <button type="button" className={styles.finishEdit} onClick={() => setEditingField(null)}>Xong</button>
              </> : <button id={`draft-${field.id}`} type="button" className={styles.fieldValue} onClick={() => { setActiveField(field.id); setEditingField(field.id); }} aria-label={`Sửa ${field.label}`}><span>{draft.values[field.id] || 'Chưa điền'}</span><PenLine size={12} aria-hidden="true" /></button>}
              <p id={`hint-${field.id}`} className={styles.fieldError}>{errors[field.id] ?? ''}</p>
            </div>)}
            <p className={styles.paperFoot}>Bố cục này giúp chỉnh sửa bản nháp. Hãy tạo và rà soát bản PDF trước khi tải xuống.</p>
          </div>}
        </div>
      </section>
      <div className={styles.chatColumn}><DraftChat key={chatEpoch} values={draft.values} onApply={edit} resetKey={chatEpoch} minimized={documentMode === 'pdf' || editingField !== null} activeField={activeField} onSelectField={selectField} /><p className={styles.privacy}><ShieldCheck size={14} aria-hidden="true" />Câu trả lời chỉ cập nhật bản nháp này. Hồ sơ tài khoản chỉ thay đổi khi bạn lưu ở trang hồ sơ.</p></div>
      <section id="document-review" className={styles.reviewBottom} aria-label="Rà soát và tải PDF">
          <div className={styles.reviewSummary}><b>{missing.length ? `${missing.length} mục còn trống` : 'Đã điền 6 mục'}</b><p>{missing.length ? `${missing.map(field => field.label).join(', ')}. Kiểm tra các mục này; thông tin không được tự suy đoán.` : 'Kiểm tra lại từng giá trị. Đã điền không có nghĩa là thông tin đã được xác minh.'}</p></div>
          <button className={`button ${styles.renderButton}`} type="button" onClick={() => renderDocument('preview')} disabled={!valid || busy !== null}>{busy === 'preview' ? <LoaderCircle className={styles.spin} size={16} aria-hidden="true" /> : <RefreshCw size={16} aria-hidden="true" />}{busy === 'preview' ? 'Đang tạo bản xem…' : 'Tạo bản PDF để rà soát'}</button>
          <label className={styles.confirm}><input type="checkbox" checked={draft.acknowledged} disabled={draft.previewRevision !== draft.revision || busy !== null} onChange={event => { const next = { ...current.current, acknowledged: event.target.checked }; current.current = next; setDraft(next); }} /><span>Tôi đã kiểm tra bản PDF, kể cả các mục còn trống.</span></label>
          <button className={`button primary ${styles.download}`} type="button" onClick={() => renderDocument('pdf')} disabled={!canDownload(draft) || busy !== null}><ArrowDownToLine size={17} aria-hidden="true" />{busy === 'pdf' ? 'Đang tạo PDF…' : 'Tải PDF thử nghiệm'}<ArrowRight size={16} aria-hidden="true" /></button><p className={styles.downloadHint}>Mỗi lần sửa đều cần tạo và kiểm tra lại bản PDF.</p>
      </section>
    </div>
    <div className={styles.feedback} aria-live="polite" role="status">{failure ? <p className={styles.failure}>{failure}</p> : notice ? <p><CircleCheck size={16} aria-hidden="true" />{notice}</p> : null}</div>
    <Link href="/portal" prefetch={false} className={styles.back}><ArrowLeft size={14} aria-hidden="true" /> Mở hồ sơ tài khoản</Link>
  </main>;
}
