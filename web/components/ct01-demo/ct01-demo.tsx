'use client';

import { useEffect, useMemo, useRef, useState, type CSSProperties, type FormEvent } from 'react';
import { createPortal, flushSync } from 'react-dom';
import Link from 'next/link';
import { ArrowUp, Check, ChevronDown, Expand, FileText, Printer, RotateCcw, X } from 'lucide-react';
import { BrandMark } from '@/components/ui/brand';
import { listenForProfilePageLifecycle } from '@/components/portal/page-lifecycle';
import { captureCt01, CT01_FIELDS, ct01DateParts, ct01SnapshotIsCurrent, editCt01Draft, EMPTY_CT01, newCt01Draft, resolveCt01Answer, SAMPLE_CT01, validateCt01, type Ct01Draft, type Ct01Field, type Ct01Snapshot, type Ct01Values } from './model';
import styles from './ct01-demo.module.css';

const PAGE = { width: 595.32, height: 842.04 };
const SOURCE_URL = 'https://congbaocdn.chinhphu.vn/CongBaoCP/VanBan/2025/7/45606/57795-1-2025981-98255-2021-tt-bca.pdf';
const DIGIT_X = [252.36, 274.44, 296.52, 318.60, 340.62, 362.64, 384.72, 406.80, 428.82, 450.84, 472.92, 495.00];
function rect(left: number, top: number, width: number, height: number): CSSProperties {
  return { left: `${left / PAGE.width * 100}%`, top: `${top / PAGE.height * 100}%`, width: `${width / PAGE.width * 100}%`, height: `${height / PAGE.height * 100}%` };
}
function MappedValues({ values }: { values: Readonly<Ct01Values> }) {
  const [day, month, year] = ct01DateParts(values.date_of_birth);
  return <div className={styles.values} aria-hidden="true">
    <span className={styles.nameValue} style={rect(225, 226, 290, 14)}>{values.full_name}</span>
    <span className={styles.dateValue} style={rect(190, 246, 47, 13)}>{day}</span>
    <span className={styles.dateValue} style={rect(246, 246, 44, 13)}>{month}</span>
    <span className={styles.dateValue} style={rect(302, 246, 83, 13)}>{year}</span>
    {/^[0-9]{12}$/.test(values.personal_id) && [...values.personal_id].map((digit, index) => <span className={styles.idDigit} key={index} style={{ left: `${DIGIT_X[index] / PAGE.width * 100}%`, top: `${270.54 / PAGE.height * 100}%` }}>{digit}</span>)}
  </div>;
}
function PrintablePages({ snapshot, ready }: { snapshot: Ct01Snapshot | null; ready: boolean }) {
  return <div className={styles.printRoot} aria-hidden="true">
    {ready && snapshot ? [1, 2].map((page) => <div className={styles.printPage} key={page}>
      <img src={`/test-fixtures/ct01/page-${page}.png`} alt="" />
      {page === 1 && <MappedValues values={snapshot.values} />}
      <span className={styles.printStamp}>BẢN THỬ NGHIỆM - DỮ LIỆU GIẢ - CHƯA HOÀN CHỈNH</span>
    </div>) : <p className={styles.printBlocked}>Chưa có bản rà soát được xác nhận. Quay lại trang thử nghiệm, kiểm tra ba mục và xác nhận trước khi in.</p>}
  </div>;
}

export function Ct01Demo() {
  const [draft, setDraft] = useState<Ct01Draft>(newCt01Draft);
  const current = useRef(draft);
  const [active, setActive] = useState<Ct01Field>('full_name');
  const [answer, setAnswer] = useState('');
  const [message, setMessage] = useState('');
  const [manualOpen, setManualOpen] = useState(false);
  const [page, setPage] = useState<1 | 2>(1);
  const [expanded, setExpanded] = useState(false);
  const [snapshot, setSnapshot] = useState<Ct01Snapshot | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [nameFits, setNameFits] = useState(true);
  const manualInput = useRef<HTMLInputElement>(null);
  const chatInput = useRef<HTMLInputElement>(null);
  const selected = CT01_FIELDS.find((field) => field.id === active)!;
  const errors = useMemo(() => ({ ...validateCt01(draft.values), ...(!nameFits ? { full_name: 'Tên chưa vừa dòng trên mẫu. Hãy rút gọn dữ liệu thử nghiệm; không in nội dung bị cắt.' } : {}) }), [draft.values, nameFits]);
  const completed = CT01_FIELDS.filter((field) => !errors[field.id]).length;
  const ready = acknowledged && ct01SnapshotIsCurrent(draft, snapshot) && Object.keys(errors).length === 0;

  function replace(next: Ct01Draft) {
    current.current = next; setDraft(next); setSnapshot(null); setAcknowledged(false);
  }
  function edit(field: Ct01Field, value: string) { replace(editCt01Draft(current.current, field, value)); }
  function clear() {
    replace({ values: { ...EMPTY_CT01 }, revision: current.current.revision + 1 });
    setAnswer(''); setMessage(''); setManualOpen(false); setActive('full_name');
  }
  useEffect(() => {
    setMounted(true);
    const stop = listenForProfilePageLifecycle(window, () => flushSync(clear), () => {});
    return stop;
  }, []);
  useEffect(() => {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) { setNameFits(false); return; }
    context.font = '11px "Times New Roman"';
    setNameFits(context.measureText(draft.values.full_name).width <= 290);
  }, [draft.values.full_name]);
  useEffect(() => { if (manualOpen) manualInput.current?.focus({ preventScroll: true }); }, [manualOpen, active]);

  function select(field: Ct01Field, manual = false) {
    setActive(field); setPage(1); setManualOpen(manual); setAnswer(''); setMessage('');
    if (!manual) chatInput.current?.focus({ preventScroll: true });
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = resolveCt01Answer(active, answer);
    if (result.kind === 'clarify') { setMessage(result.message); return; }
    edit(result.field, result.value); setAnswer('');
    setMessage(`Đã điền ${selected.label.toLocaleLowerCase('vi')} vào bản nháp. Bấm trên văn bản nếu muốn sửa.`);
    const next = CT01_FIELDS.find((field) => field.id !== active && !current.current.values[field.id]);
    if (next) setActive(next.id);
  }
  function review() {
    if (Object.keys(errors).length) { setMessage('Hãy hoàn tất ba mục thử nghiệm trước khi rà soát. Các mục còn thiếu được ghi bên dưới văn bản.'); return; }
    setSnapshot(captureCt01(current.current)); setAcknowledged(false);
  }

  return <main id="main-content" lang="vi" className={`${styles.main} ${manualOpen ? styles.manualMode : ''}`}>
    <div className={styles.compactHeader}><div><h1>CT01 <span>/ thử điền trên mẫu</span></h1><p>Ba mục thử nghiệm · Chưa phải hồ sơ hoàn chỉnh</p></div><div className={styles.headerLinks}><Link href="/research">Tra cứu</Link><Link href="/portal">Hồ sơ</Link></div></div>
    <div className={styles.testNotice}><span><b>Chỉ dùng dữ liệu giả.</b> Bản điền thử, chưa được duyệt.</span><button type="button" onClick={() => { replace({ values: { ...SAMPLE_CT01 }, revision: current.current.revision + 1 }); setAnswer(''); setMessage('Đã nạp ba giá trị giả định. Bạn có thể sửa trên văn bản hoặc qua chat.'); }}>Dùng mẫu</button></div>
    <div className={styles.workspace}>
      <section className={styles.document} aria-labelledby="ct01-document-heading">
        <div className={styles.documentBar}><div><FileText size={16} aria-hidden="true" /><h2 id="ct01-document-heading">Bản nháp CT01</h2><span>{completed}/3 mục</span></div><button type="button" onClick={() => { setExpanded(!expanded); setManualOpen(false); }} aria-expanded={expanded}>{expanded ? <ChevronDown size={15} aria-hidden="true" /> : <Expand size={15} aria-hidden="true" />}{expanded ? 'Thu gọn' : 'Xem cả trang'}</button></div>
        <div className={styles.pageTabs} role="group" aria-label="Trang tài liệu"><button type="button" aria-pressed={page === 1} onClick={() => { setPage(1); setManualOpen(false); }}>1 · Tờ khai</button><button type="button" aria-pressed={page === 2} onClick={() => { setPage(2); setManualOpen(false); }}>2 · Chú thích đầy đủ</button><span>In luôn gồm cả 2 trang</span></div>
        <div className={`${styles.paperWindow} ${expanded || page === 2 ? styles.fullPage : styles.cropped}`}>
          <div className={styles.paper}>
            <img className={styles.pageImage} src={`/test-fixtures/ct01/page-${page}.png`} alt={page === 1 ? 'Trang một mẫu CT01, tờ khai thay đổi thông tin cư trú. Ba vùng có thể sửa là họ tên, ngày sinh và số định danh.' : 'Trang hai CT01: toàn bộ chú thích và hướng dẫn từ bản Công báo gốc.'} />
            {page === 1 && <><MappedValues values={draft.values} />
              <button className={`${styles.overlay} ${active === 'full_name' ? styles.selectedOverlay : ''}`} style={rect(225, 223, 290, 18)} type="button" aria-label={`Sửa họ và tên: ${draft.values.full_name || 'chưa điền'}`} onClick={() => select('full_name', true)} />
              <button className={`${styles.overlay} ${active === 'date_of_birth' ? styles.selectedOverlay : ''}`} style={rect(190, 244, 195, 16)} type="button" aria-label={`Sửa ngày sinh: ${draft.values.date_of_birth || 'chưa điền'}`} onClick={() => select('date_of_birth', true)} />
              <button className={`${styles.overlay} ${active === 'personal_id' ? styles.selectedOverlay : ''}`} style={rect(241.3, 260.5, 264.75, 20.04)} type="button" aria-label={`Sửa số định danh: ${draft.values.personal_id || 'chưa điền'}`} onClick={() => select('personal_id', true)} />
            </>}
          </div>
        </div>
        {page === 1 && <p className={styles.paperHint}>Bấm vùng tô nhạt để sửa trực tiếp. Các mục còn lại và chữ ký giữ trống.</p>}
        {manualOpen && <div className={styles.manualEditor}><div><label htmlFor="ct01-manual">{selected.label}{active === 'date_of_birth' ? ' · YYYY-MM-DD' : ''}</label><button type="button" onClick={() => setManualOpen(false)} aria-label="Đóng chỉnh sửa trực tiếp"><X size={16} /></button></div><input ref={manualInput} id="ct01-manual" type="text" inputMode={active === 'personal_id' ? 'numeric' : 'text'} value={draft.values[active]} onChange={(event) => edit(active, event.target.value)} aria-invalid={Boolean(errors[active])} aria-describedby="ct01-manual-hint" autoComplete="off" /><p id="ct01-manual-hint">{errors[active] || 'Đã cập nhật bản nháp. Hồ sơ tài khoản không thay đổi.'}</p></div>}

      </section>
      <section className={styles.chat} aria-labelledby="ct01-chat-title">
        <div className={styles.chatHeading}><BrandMark /><div><h2 id="ct01-chat-title">Điền cùng Hồ Sơ AI</h2><p>Chat minh họa · không có AI thực</p></div></div>
        <div className={styles.fieldChips} role="group" aria-label="Chọn mục để điền">{CT01_FIELDS.map((field) => <button type="button" key={field.id} aria-pressed={active === field.id} onClick={() => select(field.id)}>{!errors[field.id] && <Check size={12} aria-hidden="true" />}{field.label}</button>)}</div>
        <div className={styles.prompt} aria-live="polite"><b>{selected.label}</b><p>{selected.prompt}</p></div>
        {message && <p className={styles.message} role="status">{message}</p>}
        <p className={styles.chatNote}>Mỗi câu trả lời điền đúng một mục đang chọn. Không lưu vào tài khoản, không suy đoán và không gửi đến dịch vụ AI.</p>
        <form className={styles.composer} onSubmit={submit}><label htmlFor="ct01-answer">{selected.label}{active === 'date_of_birth' ? ' · YYYY-MM-DD' : ''}</label><div><input ref={chatInput} id="ct01-answer" type="text" inputMode={active === 'personal_id' ? 'numeric' : 'text'} value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder={selected.placeholder} autoComplete="off" /><button type="submit" disabled={!answer.trim()} aria-label="Điền câu trả lời"><ArrowUp size={19} /></button></div><small>Nhấn Enter hoặc nút gửi để cập nhật bản nháp.</small></form>
      </section>
      <section className={styles.reviewBlock} aria-label="Rà soát bản thử nghiệm">
        <div className={styles.checkpoint}><div><b>{completed === 3 ? 'Ba mục đã có dữ liệu' : `Còn ${3 - completed} mục cần kiểm tra`}</b><button type="button" onClick={clear}><RotateCcw size={13} aria-hidden="true" />Xóa bản nháp</button></div>{Object.keys(errors).length > 0 && <ul>{CT01_FIELDS.filter((field) => errors[field.id]).map((field) => <li key={field.id}><button type="button" onClick={() => select(field.id, true)}>{errors[field.id]}</button></li>)}</ul>}<p>Đây chỉ là điểm kiểm tra ba mục, không xác nhận tờ khai đã đầy đủ hoặc đủ điều kiện nộp.</p></div>
        <div className={styles.reviewActions}><button className="button primary" type="button" onClick={review} disabled={completed !== 3}>Rà soát bản in</button><a href="/test-fixtures/ct01/blank-test-fixture.pdf" target="_blank" rel="noopener">Mở bản gốc 2 trang ↗</a></div>
        {snapshot && ct01SnapshotIsCurrent(draft, snapshot) && <section className={styles.reviewPanel} aria-labelledby="ct01-review-title"><h3 id="ct01-review-title">Kiểm tra đúng bản này</h3><dl>{CT01_FIELDS.map((field) => <div key={field.id}><dt>{field.label}</dt><dd>{snapshot.values[field.id]}</dd></div>)}</dl><p>Bản in gồm trang tờ khai và toàn bộ trang chú thích. Chọn A4, tỷ lệ 100%, tắt đầu/chân trang của trình duyệt. Có thể chọn “Lưu dưới dạng PDF” trong hộp thoại in.</p><label><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />Tôi đã kiểm tra ba giá trị này và hiểu đây là bản thử nghiệm chưa hoàn chỉnh.</label><button className="button primary" type="button" disabled={!ready} onClick={() => { if (ready) window.print(); }}><Printer size={16} aria-hidden="true" />In / Lưu PDF bằng trình duyệt</button></section>}
      </section>
    </div>
    <details className={styles.provenance}><summary>Nguồn mẫu và phạm vi thử nghiệm</summary><p>Mẫu CT01 trong Công báo số 981 + 982 ngày 26/07/2025, trang in 9–10. Bản nền hai trang được giữ nguyên; lớp điền thử chỉ phủ ba mục trên trang đầu.</p><a href={SOURCE_URL} target="_blank" rel="noopener">Xem nguồn Công báo ↗</a><p>Mã SHA-256 của bản nền: <code>ba72c63d656c2b3b0702faaef3f7a51c0356847631f16b47e7c354b8f5965444</code></p><p>In qua trình duyệt tạo bản hình ảnh có chữ phủ, không tạo PDF có trường điền tương tác. Chưa xác minh tính hợp lệ cho một hồ sơ thực tế.</p></details>
    {mounted && createPortal(<PrintablePages snapshot={snapshot} ready={ready} />, document.body)}
  </main>;
}
