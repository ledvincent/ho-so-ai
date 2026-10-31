'use client';
import { useLocale } from '@/components/ui/locale';
import type { DocumentEvidence, FormAction } from './document-model';
import styles from './chat.module.css';

export function DocumentCards({ evidence, onOpen, busy = false }: { evidence: DocumentEvidence; onOpen?: (action: FormAction) => void; busy?: boolean }) {
  const { t } = useLocale();
  if (!evidence.documents.length) return null;
  return <section className={styles.documentCards} aria-label={t('Tài liệu và hướng dẫn có nguồn')}><h2>{t('Tài liệu và hướng dẫn có nguồn')}</h2><p>{t('Điều kiện và phiên bản cần được kiểm tra riêng. Một hướng dẫn nộp hồ sơ không phải là một giấy tờ bổ sung.')}</p>{evidence.documents.map(card => <article key={card.id}>
    <div className={styles.cardMeta}><span>{t(card.kind === 'fillable_form' ? 'Biểu mẫu có quy trình điền' : card.kind === 'submission_instruction' ? 'Hướng dẫn nộp hồ sơ' : 'Giấy tờ chuẩn bị riêng')}</span><b>{t(card.requirement === 'required' ? 'Theo nguồn: cần chuẩn bị' : card.requirement === 'conditional' ? 'Có điều kiện' : 'Chưa xác nhận áp dụng')}</b></div>
    <h3>{card.title}</h3>{card.condition && <p><strong>{t('Điều kiện:')}</strong> {card.condition}</p>}{card.description && <p>{card.description}</p>}
    {card.kind !== 'submission_instruction' && <small>{t('Bản chính:')} {card.originals ?? t('Chưa rõ')} · {t('Bản sao:')} {card.copies ?? t('Chưa rõ')}</small>}
    <details className={styles.sourceDetails}><summary>{t('Nguồn và chi tiết')}</summary><small>{t('Tình trạng bằng chứng:')} {card.evidence_status}</small><div className={styles.cardSources}>{card.source_ids.map(id => { const source = evidence.citations.find(item => item.id === id); return source ? <a key={id} href={source.url} target="_blank" rel="noopener">[{source.id}] {source.title} ↗</a> : null; })}</div></details>
    {card.form ? <><p className={styles.warning}>{t('Ấn bản biểu mẫu và điều kiện áp dụng cần được cơ quan tiếp nhận xác nhận.')}</p>{onOpen && <button type="button" disabled={busy} onClick={() => onOpen(card.form!)}>{t('Xem thủ tục và tài liệu trước khi mở bản nháp')}</button>}<details><summary>{t('Chi tiết tài liệu nguồn')}</summary><small>{card.form.revision} · {card.form.review_status} · {card.form.applicability}<br />{card.form.document_id}<br />{card.form.template_version}<br />{card.form.template_sha256}</small></details></> : <p className={styles.warning}>{t('Chuẩn bị riêng · không mở nhầm biểu mẫu khác.')}</p>}
  </article>)}<p>{t('Danh sách này là ngữ cảnh có nguồn, không xác nhận hồ sơ được chấp nhận hoặc đúng ấn bản pháp lý.')}</p></section>;
}
