'use client';
import { useLocale } from '@/components/ui/locale';

import { useState } from 'react';
import type { ProcedureDetail } from './model';
import styles from './chat.module.css';

export function DossierChecklist({ detail }: { detail: ProcedureDetail }) {
  const { t } = useLocale();
  const [progress, setProgress] = useState<Record<number, string>>({});
  const requirements = detail.requirements;
  return <details className={styles.dossier}><summary>{t("Thành phần hồ sơ · theo dõi chuẩn bị")}</summary>
    <p>{detail.fixture ? t("Tình huống giả lập. ") : ''}{t("Các mục dưới đây giữ nguyên lời nguồn, có thể gồm hướng dẫn, điều kiện hoặc lựa chọn thay thế. Không phải mỗi mục đều là một giấy tờ bắt buộc. Trạng thái chuẩn bị do bạn tự ghi; không xác nhận hồ sơ đầy đủ hay được cơ quan chấp nhận.")}</p>
    {detail.sourceVersion && <details><summary>{t("Chi tiết phiên bản nguồn")}</summary><small className={styles.sourceVersion}>{t("SHA-256: ")}{detail.sourceVersion}</small></details>}
    {detail.sourceUrl && <p><a href={detail.sourceUrl} target="_blank" rel="noopener">{t("Đối chiếu nguồn thủ tục ↗")}</a>{detail.fetchedAt && <small>{t("Thời điểm lấy nguồn: ")}{detail.fetchedAt} {t(" · không phải ngày hiệu lực pháp lý")}</small>}</p>}
    {!requirements?.length ? <p>{t("Chưa có danh sách yêu cầu có nguồn để hiển thị. Mức độ sẵn sàng của toàn bộ hồ sơ chưa xác định.")}</p> : requirements.map(item => <article key={item.id}>
      <small>{t("Nguyên văn nguồn · không dịch tự động")}</small>{item.groupHeading && <h3>{item.groupHeading}</h3>}<p className={styles.verbatim}>{item.text}</p>
      <small>{t("Số lượng theo nguồn · Bản chính: ")}{item.originals ?? t('Chưa rõ')} {t(" · Bản sao: ")}{item.copies ?? t('Chưa rõ')}</small>
      {item.formIds.map(id => { const form = detail.forms.find(form => form.id === id); const pending = detail.otherForms?.find(form => form.id === id); return <div key={id} className={styles.requirementForm}>{form ? <>{form.label} {t(" · ứng viên tài liệu · ")}{form.reviewStatus === 'draft' ? t("Bản nháp, chờ duyệt") : form.reviewStatus === 'unknown' ? t('Chưa rõ trạng thái duyệt') : form.reviewStatus ?? t('Chưa rõ trạng thái duyệt')}{form.revision ? ` · ${form.revision}` : ''}{form.href && <> {t(" · ")}<a href={form.href} target="_blank" rel="noopener">{t("Xem tài liệu nguồn ↗")}</a></>}<details><summary>{t("Chi tiết tài liệu nguồn")}</summary><small>{t("SHA-256: ")}{form.sha256}</small></details></> : <>{pending?.label ?? t('Tài liệu liên quan')} {t(" · chưa có phiên bản để mở quy trình điền")}</>}</div>; })}
      <label>{t("Theo dõi cá nhân ")}<select aria-label={t(`Chuẩn bị mục nguồn ${item.position + 1}`)} value={progress[item.id] ?? 'unknown'} onChange={event => setProgress(previous => ({ ...previous, [item.id]: event.target.value }))}><option value="unknown">{t("Chưa kiểm tra / chưa rõ áp dụng")}</option><option value="preparing">{t("Đang chuẩn bị")}</option><option value="reviewed">{t("Đã tự kiểm tra theo điều kiện nguồn")}</option></select></label>
    </article>)}
    <h3>{t("Tài liệu gắn với thủ tục")}</h3><p>{t("Liên kết trong nguồn không tự xác nhận tài liệu là bắt buộc hay đúng ấn bản cho trường hợp của bạn. Chỉ NA5 tương thích đã chọn được mở trình điền; tài liệu khác chỉ xem hoặc chuẩn bị thủ công.")}</p>
    {detail.forms.map(form => <div key={form.sha256}>{form.href ? <a href={form.href} target="_blank" rel="noopener">{form.label} {t(" ↗")}</a> : form.label} {t(" · ")}{form.reviewStatus === 'draft' ? t("Bản nháp, chờ duyệt") : form.reviewStatus ?? 'Chưa rõ trạng thái duyệt'}<details><summary>{t("Chi tiết tài liệu nguồn")}</summary><small className={styles.sourceVersion}>{form.sha256}</small></details></div>)}
    {detail.otherForms?.map(form => <p key={form.id}>{form.label} {t(" · chưa tải bản nguồn")}</p>)}
    {!detail.forms.length && !detail.otherForms?.length && <p>{t("Chưa có tài liệu gắn với thủ tục để hiển thị.")}</p>}
    <p>{t("Tiến độ của NA5 ở phía trên chỉ phản ánh các mục của bản nháp hiện tại. Toàn bộ hồ sơ, điều kiện áp dụng và ấn bản tài liệu vẫn cần kiểm tra riêng.")}</p>
  </details>;
}
