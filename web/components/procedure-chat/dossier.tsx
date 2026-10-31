'use client';
import { useLocale } from '@/components/ui/locale';
import type { ProcedureDetail } from './model';
import { candidateLabel, guideFor, guideText } from './guide-projection';
import styles from './chat.module.css';

/** Display projection only. Original source rows and workflow gates remain intact. */
export function DossierChecklist({ detail, compact = false }: { detail: ProcedureDetail; compact?: boolean }) {
  const { locale, t } = useLocale();
  const guide = guideFor(detail);
  const body = <div className={styles.guideBody}>
    {detail.fixture && <p className={styles.guideNotice}>{t('Tình huống giả lập, không phải hướng dẫn pháp lý.')}</p>}
    <section aria-label={t('Giấy tờ cần chuẩn bị')}><h3>{t('Giấy tờ cần chuẩn bị')}</h3>
      {guide ? <ul className={styles.guideDocuments}>{guide.checklist.filter(item => item.kind === 'document').map((document, index) => <li key={index}><h4>{guideText(document.title, locale)}</h4><p>{guideText(document.text, locale)}</p><p className={styles.guideQuantity}>{t('Bản chính:')} {document.originals ?? t('Chưa rõ')} · {t('Bản sao:')} {document.copies ?? t('Chưa rõ')}</p>{document.condition && <p className={styles.guideCondition}><b>{t('Điều kiện:')}</b> {guideText(document.condition, locale)}</p>}</li>)}</ul> : <p>{t('Chưa có bản hướng dẫn đã đối chiếu cho phiên bản nguồn này. Xem nguyên văn trong phần nguồn bên dưới; điều kiện áp dụng chưa được xác nhận.')}</p>}
    </section>
    <section aria-label={t('Các bước thực hiện')}><h3>{t('Các bước thực hiện')}</h3>{guide ? <ol className={styles.guideSteps}>{guide.steps.map((step, index) => <li key={step.id}><h4>{guideText(step.title, locale)}</h4><p>{guideText(step.text, locale)}</p></li>)}</ol> : <p>{t('Các bước thực hiện chưa được đối chiếu cho phiên bản nguồn này. Không suy ra bước nộp hồ sơ từ tên biểu mẫu.')}</p>}</section>
    {guide?.checklist.filter(item => item.kind === 'submission_instruction').map(item => <aside className={styles.guideInstruction} key={item.id}><h4>{guideText(item.title, locale)}</h4><p>{guideText(item.text, locale)}</p>{item.condition && <p>{guideText(item.condition, locale)}</p>}</aside>)}
    {Boolean(guide?.conditions.length) && <section><h3>{t('Điều kiện cần kiểm tra')}</h3><ul className={styles.guideSteps}>{guide!.conditions.map((condition, index) => <li key={index}>{guideText(condition.text, locale)}</li>)}</ul></section>}
    {guide && <p className={styles.guideNotice}>{t('Xác nhận điều kiện áp dụng và ấn bản biểu mẫu với cơ quan tiếp nhận. Bản hướng dẫn chưa xác nhận hồ sơ được chấp nhận.')}</p>}
    <details className={styles.sourceDetails}><summary>{t('Nguồn và chi tiết')}</summary>
      {detail.sourceUrl && <p><a href={detail.sourceUrl} target="_blank" rel="noopener">{t('Mở nguồn thủ tục chính thức')} ↗</a></p>}
      {guide?.notes.map((notice, index) => <p key={index}>{guideText(notice, locale)}</p>)}
      <h4>{t('Nguyên văn tiếng Việt')}</h4>
      {detail.sourceSections?.map((section, index) => <details className={styles.originalRow} key={index}><summary lang="vi">{section.heading}</summary><p lang="vi">{section.text}</p></details>)}
      {!detail.requirements?.length && <p>{t('Chưa có nguyên văn thành phần hồ sơ để hiển thị.')}</p>}
      {detail.requirements?.map(item => <div className={styles.originalRow} key={item.id}>{item.groupHeading && <h4 lang="vi">{item.groupHeading}</h4>}<p lang="vi">{item.text}</p><small>{t('Bản chính:')} {item.originals ?? t('Chưa rõ')} · {t('Bản sao:')} {item.copies ?? t('Chưa rõ')}</small></div>)}
      {detail.forms.length > 0 && <><h4>{t('Tài liệu nguồn')}</h4>{detail.forms.map(form => <p key={form.sha256}>{form.href ? <a href={form.href} target="_blank" rel="noopener">{form.label} ↗</a> : form.label}<small>{form.revision} · {form.reviewStatus}<br />{form.sha256}</small></p>)}</>}
      {detail.otherForms?.map(form => <p key={form.id}>{form.label} · {t('Chưa tải bản nguồn')}</p>)}
      <dl><div><dt>{t('Bản chụp nguồn')}</dt><dd>{detail.sourceVersion ?? t('Chưa rõ')}</dd></div><div><dt>{t('Thời điểm lấy nguồn')}</dt><dd>{detail.fetchedAt ?? t('Chưa rõ')}</dd></div></dl>
      <small>{t('Thời điểm lấy nguồn không phải ngày hiệu lực pháp lý. Bản hướng dẫn giúp chuẩn bị hồ sơ; cơ quan tiếp nhận xác nhận điều kiện và ấn bản áp dụng.')}</small>
    </details>
  </div>;
  return compact ? <details className={styles.guideCompact}><summary>{t('Hướng dẫn thủ tục')} · {candidateLabel(detail.candidate, locale)}</summary>{body}</details> : <section className={styles.guide} aria-label={t('Hướng dẫn thủ tục')}>{body}</section>;
}
