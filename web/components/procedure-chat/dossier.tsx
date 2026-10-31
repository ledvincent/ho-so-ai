'use client';
import { useState } from 'react';
import type { ProcedureDetail } from './model';
import styles from './chat.module.css';

export function DossierChecklist({ detail }: { detail: ProcedureDetail }) {
  const [progress, setProgress] = useState<Record<number, string>>({});
  const requirements = detail.requirements;
  return <details className={styles.dossier}><summary>Thành phần hồ sơ · theo dõi chuẩn bị</summary>
    <p>{detail.fixture ? 'Tình huống giả lập. ' : ''}Các mục dưới đây giữ nguyên lời nguồn, có thể gồm hướng dẫn, điều kiện hoặc lựa chọn thay thế. Không phải mỗi mục đều là một giấy tờ bắt buộc. Trạng thái chuẩn bị do bạn tự ghi; không xác nhận hồ sơ đầy đủ hay được cơ quan chấp nhận.</p>
    {detail.sourceVersion && <small className={styles.sourceVersion}>Bản nguồn: {detail.sourceVersion}</small>}
    {!requirements?.length ? <p>Chưa có danh sách yêu cầu có nguồn để hiển thị. Mức độ sẵn sàng của toàn bộ hồ sơ chưa xác định.</p> : requirements.map(item => <article key={item.id}>
      {item.groupHeading && <h3>{item.groupHeading}</h3>}<p className={styles.verbatim}>{item.text}</p>
      <small>Số lượng theo nguồn · Bản chính: {item.originals ?? 'Chưa rõ'} · Bản sao: {item.copies ?? 'Chưa rõ'}</small>
      {item.formIds.map(id => { const form = detail.forms.find(form => form.id === id); const pending = detail.otherForms?.find(form => form.id === id); return <p key={id} className={styles.requirementForm}>{form ? <>{form.label} · ứng viên tài liệu · {form.reviewStatus ?? 'Chưa rõ trạng thái duyệt'}{form.revision ? ` · ${form.revision}` : ''}{form.href && <> · <a href={form.href} target="_blank" rel="noopener">Xem tài liệu nguồn ↗</a></>}<small>SHA-256: {form.sha256}</small></> : <>{pending?.label ?? 'Tài liệu liên quan'} · chưa có phiên bản để mở quy trình điền</>}</p>; })}
      <label>Theo dõi cá nhân <select aria-label={`Chuẩn bị mục nguồn ${item.position + 1}`} value={progress[item.id] ?? 'unknown'} onChange={event => setProgress(previous => ({ ...previous, [item.id]: event.target.value }))}><option value="unknown">Chưa kiểm tra / chưa rõ áp dụng</option><option value="preparing">Đang chuẩn bị</option><option value="reviewed">Đã tự kiểm tra theo điều kiện nguồn</option></select></label>
    </article>)}
    <h3>Tài liệu gắn với thủ tục</h3><p>Liên kết trong nguồn không tự xác nhận tài liệu là bắt buộc hay đúng ấn bản cho trường hợp của bạn. Chỉ NA5 tương thích đã chọn được mở trình điền; tài liệu khác chỉ xem hoặc chuẩn bị thủ công.</p>
    {detail.forms.map(form => <p key={form.sha256}>{form.href ? <a href={form.href} target="_blank" rel="noopener">{form.label} ↗</a> : form.label} · {form.reviewStatus ?? 'Chưa rõ trạng thái duyệt'}<small className={styles.sourceVersion}>{form.sha256}</small></p>)}
    {detail.otherForms?.map(form => <p key={form.id}>{form.label} · chưa tải bản nguồn</p>)}
    {!detail.forms.length && !detail.otherForms?.length && <p>Chưa có tài liệu gắn với thủ tục để hiển thị.</p>}
    <p>Tiến độ của NA5 ở phía trên chỉ phản ánh các mục của bản nháp hiện tại. Toàn bộ hồ sơ, điều kiện áp dụng và ấn bản tài liệu vẫn cần kiểm tra riêng.</p>
  </details>;
}
