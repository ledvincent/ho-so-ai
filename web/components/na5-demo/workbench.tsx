'use client';

import { useEffect, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import { flushSync } from 'react-dom';
import Link from 'next/link';
import { ArrowUp, Check, Expand, FileText, LockKeyhole, X } from 'lucide-react';
import { BrandMark } from '@/components/ui/brand';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import pageData from '@/public/test-fixtures/na5/pages.json';
import { activeFields, canDownload, captureReview, editableFields, emptyValues, example, issues, payloadValues, PROCEDURE_TITLE, resolveLiteral, schema, updateValue, type Placement, type Review, type Values, type WorkflowField } from './model';
import { assistantRequest, mockTransport, type ChatResponse } from './transport';
import styles from './workbench.module.css';

function position(placement: Placement): CSSProperties {
  const page = pageData[placement.page - 1]; const [x0, y0, x1, y1] = placement.bbox;
  return { left: `${x0 / page.width * 100}%`, top: `${y0 / page.height * 100}%`, width: `${(x1 - x0) / page.width * 100}%`, height: `${(y1 - y0) / page.height * 100}%` };
}
function parts(field: WorkflowField, value: string): { placement: Placement; text: string; size: number; overflow: boolean }[] {
  if (!value) return [];
  if (field.marks) { const placement = field.marks[value]; return placement ? [{ placement, text: '×', size: 11, overflow: false }] : []; }
  let texts = [value];
  const context = typeof document === 'undefined' ? null : document.createElement('canvas').getContext('2d');
  const width = (text: string, size: number) => { if (!context) return text.length * size * .6; context.font = `${size}px Arial`; return context.measureText(text).width; };
  if (field.type === 'date') {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return [];
    const [year, month, day] = value.split('-'); const components: Record<string, string> = { year, month, day };
    texts = field.placements.map(p => components[p.component ?? ''] ?? '');
  } else if (field.repeat) texts = field.placements.map(() => value);
  else if (field.multiline && field.placements.length) {
    const max = Math.min(...field.placements.map(p => p.bbox[2] - p.bbox[0])) - 2;
    texts = [''];
    for (const word of value.split(/\s+/)) { const next = `${texts[texts.length - 1]} ${word}`.trim(); if (width(next, 9) > max) texts.push(word); else texts[texts.length - 1] = next; }
  }
  return field.placements.flatMap((placement, index) => {
    const text = texts[index]; if (!text) return [];
    let size = 10; const max = placement.bbox[2] - placement.bbox[0] - 2;
    while (size > 7.5 && width(text, size) > max) size -= .25;
    return [{ placement, text, size, overflow: width(text, size) > max || texts.length > field.placements.length }];
  });
}

export function Na5Workbench() {
  const [values, setValues] = useState<Values>(emptyValues);
  const [revision, setRevision] = useState(1);
  const [activeId, setActiveId] = useState('applicant_full_name');
  const [answer, setAnswer] = useState('');
  const [message, setMessage] = useState('');
  const [manual, setManual] = useState(false);
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState(false);
  const [mode, setMode] = useState<'field' | 'question'>('field');
  const [assistant, setAssistant] = useState<ChatResponse | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const generation = useRef(0);
  const paperWindow = useRef<HTMLDivElement>(null);
  const manualInput = useRef<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement | null>(null);
  const editable = editableFields(values);
  const selected = editable.find(field => field.id === activeId) ?? editable[0];
  const errors = issues(values);
  const mapped = activeFields(values).flatMap(field => parts(field, (values[field.id] ?? '').trim()).map(part => ({ ...part, field })));
  for (const part of mapped) if (part.overflow) errors[part.field.id] = `Nội dung chưa vừa vùng điền: ${part.field.label}.`;
  const remaining = Object.keys(errors).length;
  const currentReview = review?.revision === revision ? review : null;
  // No mock transport token: only the real reviewed backend may unlock download.
  const downloadReady = canDownload(schema.review_status, currentReview, revision, null, confirmed);
  const target = selected.placements.find(item => item.page === page) ?? selected.placements[0];
  const crop: CSSProperties = target ? { '--focus-top': `${Math.max(0, target.bbox[1] - 50) / pageData[page - 1].height * 100}%`, '--focus-left': `${50 - ((target.bbox[0] + target.bbox[2]) / 2) / pageData[page - 1].width * 170}%` } as CSSProperties : { '--focus-top': '14%', '--focus-left': '-25%' } as CSSProperties;

  function invalidate() { generation.current += 1; setRevision(value => value + 1); setReview(null); setConfirmed(false); setAssistant(null); }
  function edit(id: string, value: string) { setValues(previous => updateValue(previous, id, value)); invalidate(); setMessage('Đã cập nhật cùng bản nháp NA5.'); }
  function clear() { invalidate(); setValues(emptyValues()); setActiveId('applicant_full_name'); setAnswer(''); setMessage(''); setManual(false); setBusy(false); setPage(1); }
  function select(id: string, openManual = false) {
    const field = editable.find(item => item.id === id); if (!field) return;
    setActiveId(id); setAnswer(''); setMessage(''); setManual(openManual); setMode('field');
    if (field.placements.length) setPage(field.placements[0].page);
  }
  useEffect(() => listenForProfilePageLifecycle(window, () => flushSync(clear), () => {}), []);
  useEffect(() => { if (manual) manualInput.current?.focus({ preventScroll: true }); }, [manual, activeId]);
  useEffect(() => {
    if (!target || !paperWindow.current || expanded || matchMedia('(max-width:760px)').matches) return;
    const area = paperWindow.current; const scale = area.clientWidth / pageData[page - 1].width;
    area.scrollTo({ top: Math.max(0, target.bbox[1] * scale - 125), behavior: 'instant' });
  }, [activeId, page, expanded]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (mode === 'question') {
      if (answer.trim().length < 2 || answer.trim().length > 1000) { setMessage('Câu hỏi cần từ 2 đến 1000 ký tự.'); return; }
      const attempt = ++generation.current; setBusy(true);
      const response = await mockTransport.chat(assistantRequest(answer.trim()));
      if (attempt === generation.current) { setAssistant(response); setAnswer(''); setBusy(false); }
      return;
    }
    const result = resolveLiteral(selected, answer);
    if ('clarification' in result) { setMessage(result.clarification); return; }
    edit(selected.id, result.value); setAnswer('');
    if (selected.id === 'host_type') {
      const nextId = result.value === 'family' ? 'sponsor_kind' : 'organisation_name';
      setActiveId(nextId);
      const nextField = schema.fields.find(field => field.id === nextId);
      if (nextField?.placements.length) setPage(nextField.placements[0].page);
    }
  }
  function reviewDraft() { if (!remaining) { setReview(captureReview(values, revision)); setConfirmed(false); setManual(false); } }
  function manualControl() {
    const common = { id: 'na5-manual', value: values[selected.id] ?? '', onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => edit(selected.id, event.target.value), 'aria-invalid': Boolean(errors[selected.id]) };
    if (selected.options) return <select {...common} ref={node => { manualInput.current = node; }}><option value="">Chọn…</option>{selected.options.map(option => <option key={option} value={option}>{option}</option>)}</select>;
    if (selected.multiline) return <textarea {...common} rows={2} ref={node => { manualInput.current = node; }} autoComplete="off" />;
    return <input {...common} ref={node => { manualInput.current = node; }} autoComplete="off" placeholder={selected.type === 'date' ? 'YYYY-MM-DD' : selected.label} />;
  }

  return <main id="main-content" className={`${styles.main} ${manual ? styles.manualMode : ''}`}>
    <header className={styles.title}><div><h1>NA5 <span>· Gia hạn tạm trú</span></h1><p>{PROCEDURE_TITLE} · <b>{schema.procedure_code}</b></p></div><Link href="/demo/research">Tra cứu thủ tục →</Link></header>
    <div className={styles.notice}><span><b>Demo · dữ liệu giả.</b> Mẫu và bản đồ điền đang chờ duyệt. Chưa kết nối backend.</span><button type="button" onClick={() => { invalidate(); setValues(payloadValues(example)); setAnswer(''); setMessage('Đã nạp ví dụ giả định từ bộ kiểm tra của Vincent.'); setManual(false); }}>Dùng mẫu</button></div>
    <div className={styles.workspace}>
      <section className={styles.document} aria-labelledby="na5-document-title">
        <div className={styles.documentBar}><h2 id="na5-document-title"><FileText size={16} />Bản nháp NA5</h2><button type="button" onClick={() => setExpanded(!expanded)} aria-expanded={expanded}><Expand size={14} />{expanded ? 'Thu gọn' : 'Xem cả trang'}</button></div>
        <div className={styles.pages} role="group" aria-label="Trang NA5">{pageData.map(item => <button type="button" key={item.page} aria-pressed={page === item.page} onClick={() => { setPage(item.page); setExpanded(true); }}>{item.page === 3 ? '3 · Chú thích' : `${item.page} · Tờ khai`}</button>)}<span>{schema.revision} · Draft</span></div>
        <div ref={paperWindow} className={`${styles.paperWindow} ${expanded ? styles.expanded : ''}`}>
          <div className={styles.paper} style={crop}><img src={`/test-fixtures/na5/page-${page}.png`} alt={`Trang ${page} của mẫu NA5 từ bản gốc Vincent, thủ tục 1.001146.`} />
            {mapped.filter(part => part.placement.page === page).map((part, index) => <span key={`${part.field.id}-${index}`} className={`${styles.value} ${part.overflow ? styles.overflow : ''}`} style={{ ...position(part.placement), fontSize: `${part.size / pageData[page - 1].width * 100}cqw` }} aria-hidden="true">{part.overflow ? '↗' : part.text}</span>)}
            {activeFields(values).flatMap(field => field.placements.filter(p => p.page === page).map((placement, index) => <button key={`${field.id}-${index}`} className={`${styles.overlay} ${selected.id === field.id ? styles.active : ''}`} style={position(placement)} type="button" disabled={Object.hasOwn(schema.fixed_values, field.id)} aria-label={`Sửa ${field.label}${field.placements.length > 1 ? ` (${index + 1})` : ''}`} onClick={() => select(field.id, true)} />))}
          </div>
        </div>
        <p className={styles.paperHint}>Bấm vùng điền để sửa. Chữ ký, xác nhận và con dấu được giữ trống.</p>
        {manual && <div className={styles.manual}><div><label htmlFor="na5-manual">{selected.label}</label><button type="button" aria-label="Đóng chỉnh sửa trực tiếp" onClick={() => setManual(false)}><X size={16} /></button></div>{manualControl()}<p>{errors[selected.id] ?? 'Đã cập nhật bản nháp; không lưu hồ sơ tài khoản.'}</p></div>}
      </section>
      <section className={styles.chat} aria-labelledby="na5-chat-title">
        <header className={styles.chatHeading}><BrandMark /><div><h2 id="na5-chat-title">Điền cùng Hồ Sơ AI</h2><p>NA5 · {schema.procedure_code} · {mode === 'field' ? 'Điền theo mục' : 'Hỏi có nguồn'}</p></div></header>
        <div className={styles.modes}><button type="button" aria-pressed={mode === 'field'} onClick={() => { setMode('field'); setAnswer(''); }}>Điền mục</button><button type="button" aria-pressed={mode === 'question'} onClick={() => { setMode('question'); setAnswer(''); setManual(false); }}>Hỏi về thủ tục</button></div>
        <div className={styles.conversation}>
          {mode === 'field' ? <><label className={styles.selectorLabel} htmlFor="na5-field">Mục đang điền</label><select id="na5-field" value={selected.id} onChange={event => select(event.target.value)}>{editable.map(field => <option key={field.id} value={field.id}>{field.label}{field.required ? ' *' : ''}</option>)}</select>
            <div className={styles.quickFields}>{['applicant_full_name', 'birth_date', 'passport_number', 'host_type'].map(id => <button key={id} type="button" aria-pressed={selected.id === id} onClick={() => select(id)}>{({ applicant_full_name: 'Họ tên', birth_date: 'Ngày sinh', passport_number: 'Hộ chiếu', host_type: 'Bảo lãnh' } as Record<string, string>)[id]}</button>)}</div>
            <div className={styles.prompt}><b>{selected.label}{selected.required ? ' *' : ''}</b><p>{selected.options ? 'Chọn đúng một giá trị theo mẫu bên dưới.' : selected.type === 'date' ? 'Nhập ngày giả định theo YYYY-MM-DD. Không tự suy đoán ngày và tháng.' : 'Nhập một giá trị giả định. Câu trả lời điền vào đúng mục đang chọn.'}</p>{selected.options && <div className={styles.choices}>{selected.options.map(option => <button type="button" key={option} aria-pressed={values[selected.id] === option} onClick={() => edit(selected.id, option)}>{option}</button>)}</div>}</div>
            <dl className={styles.current}><dt>Giá trị trên bản nháp</dt><dd>{values[selected.id] || 'Chưa điền'}</dd></dl></> : <div className={styles.prompt}><b>{PROCEDURE_TITLE}</b><p>Phản hồi tra cứu sẽ gồm câu trả lời và trích dẫn. Phản hồi không tự thay đổi các mục trên NA5.</p></div>}
          {message && <p className={styles.message} role="status">{message}</p>}
          {assistant && <div className={styles.assistant} role="status"><b>Demo · {assistant.status}</b><p>{assistant.answer}</p><span>Chưa có trích dẫn · Không đổi bản nháp</span></div>}
        </div>
        <form className={styles.composer} onSubmit={submit}><label htmlFor="na5-answer">{mode === 'question' ? 'Câu hỏi về thủ tục 1.001146' : selected.label}</label><div><input id="na5-answer" value={answer} onChange={event => setAnswer(event.target.value)} autoComplete="off" placeholder={mode === 'question' ? 'Dịch vụ tra cứu chưa kết nối' : selected.type === 'date' ? 'YYYY-MM-DD' : 'Nhập dữ liệu giả'} /><button type="submit" disabled={!answer.trim() || busy} aria-label="Gửi câu trả lời NA5"><ArrowUp size={18} /></button></div><small>{mode === 'field' ? 'Chat điền theo kịch bản · Không suy luận bằng AI' : 'Mock phản hồi đúng cấu trúc của dịch vụ Vincent'}</small></form>
      </section>
      <section className={styles.review} aria-label="Rà soát NA5">
        <div className={styles.reviewHeading}><b>{remaining ? `${remaining} mục cần kiểm tra` : 'Các mục đang áp dụng đã có dữ liệu'}</b><button type="button" onClick={clear}>Xóa bản nháp</button></div>
        <p>Loại yêu cầu cố định: <b>stay_extension</b>. Dấu * theo quy tắc hoàn thiện của schema, không phải xác nhận pháp lý.</p>
        {remaining > 0 && <details><summary>Xem các mục cần kiểm tra</summary><ul>{Object.entries(errors).map(([id, error]) => <li key={id}><button type="button" onClick={() => select(id, true)}>{error}</button></li>)}</ul></details>}
        <div className={styles.actions}><button type="button" className="button primary" disabled={remaining > 0} onClick={reviewDraft}>Rà soát bản nháp NA5</button><a href="/test-fixtures/na5/blank.pdf" target="_blank" rel="noopener">Mở mẫu gốc 3 trang ↗</a></div>
        {currentReview && <div className={styles.reviewSnapshot}><p><Check size={15} />Bản rà soát giữ đúng {Object.keys(currentReview.values).length} giá trị đang áp dụng. Sửa bất kỳ mục nào sẽ hủy xác nhận.</p><details><summary>Đối chiếu giá trị đã chốt</summary><dl>{Object.entries(currentReview.values).map(([id, value]) => <div key={id}><dt>{schema.fields.find(field => field.id === id)?.label ?? id}</dt><dd>{value || 'Trống'}</dd></div>)}</dl></details><label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />Tôi đã xem các giá trị của bản nháp này.</label></div>}
        <button className={`button ${styles.download}`} type="button" disabled={!downloadReady}><LockKeyhole size={16} />Tải NA5 · Chờ duyệt mẫu</button><p>Trạng thái mẫu: <b>{schema.review_status}</b>. Bản xem PDF và X-Review-Token từ backend chưa kết nối; demo không tạo token, không bỏ qua duyệt mẫu.</p>
      </section>
    </div>
    <details className={styles.provenance}><summary>Nguồn mẫu và phạm vi demo</summary><p>Vincent: 9386f428e6794acd0a8b9e4cb3cc759bf5c989b4 · NA5 · {schema.procedure_code}. Mẫu đang chờ người duyệt. Bản nháp hiển thị cục bộ, chưa phải PDF do backend tạo.</p><a href="https://congan.cantho.gov.vn/uploads/thu-tuc-hanh-chinh/na5_4.doc" target="_blank" rel="noopener">Nguồn được ghi trong hồ sơ mẫu ↗</a><p>Không sao chép quốc tịch gốc từ quốc tịch hiện nay; không ánh xạ địa chỉ hồ sơ chung vào địa chỉ tạm trú. Chưa tích hợp hồ sơ tài khoản.</p><Link href="/demo/ct01">Mở thử nghiệm CT01 riêng</Link></details>
  </main>;
}
