'use client';
import { useLocale } from '@/components/ui/locale';

import type { FormEvent } from 'react';
import styles from './profile.module.css';

/** Presentation descriptors only. The owner-delivered DTO adapter supplies IDs. */
export type ProfileInput = { id: string; label: string; section: 'basics' | 'contact' | 'passport' | 'residence'; kind?: 'text' | 'date' | 'email' | 'tel'; multiline?: boolean; maxLength?: number; hint?: string; options?: readonly { value: string; label: string }[] };
const sections = [
  { id: 'basics', title: 'Thông tin cơ bản', description: 'Thông tin của bạn, dùng lại khi phù hợp với biểu mẫu.' },
  { id: 'contact', title: 'Liên hệ', description: 'Chọn những thông tin bạn muốn lưu để liên hệ.' },
  { id: 'passport', title: 'Hộ chiếu', description: 'Ghi đúng theo giấy tờ; có thể để trống nếu chưa cần.' },
  { id: 'residence', title: 'Cư trú', description: 'Phân biệt rõ địa chỉ chung và nơi tạm trú tại Việt Nam.' },
] as const;

export function ProfileSections({ fields, values, onEdit, onSave, onCancel, busy, editable, dirty, problem, saved }: { fields: ProfileInput[]; values: Record<string, string | null>; onEdit: (id: string, value: string) => void; onSave: () => void; onCancel: () => void; busy: boolean; editable: boolean; dirty: boolean; problem?: string; saved: boolean }) {
  const { t } = useLocale();
  function submit(event: FormEvent) { event.preventDefault(); if (!busy && editable && dirty) onSave(); }
  return <form className={styles.editor} onSubmit={submit} autoComplete="off">
    <p className={styles.optional}>{t("Tất cả các mục đều tùy chọn. Bạn có thể tiếp tục trò chuyện mà không hoàn tất hồ sơ.")}</p>
    {problem && <p className={styles.problem} role="alert">{t(problem)}</p>}
    <div className={styles.sections}>{sections.map(section => <fieldset key={section.id} disabled={!editable || busy}><legend>{t(section.title)}</legend><p>{t(section.description)}</p><div className={styles.fields}>{fields.filter(field => field.section === section.id).map(field => <div key={field.id} className={field.multiline ? styles.wide : ''}><label htmlFor={`saved-${field.id}`}>{t(field.label)}</label>{field.options ? <select id={`saved-${field.id}`} value={values[field.id] ?? ''} onChange={event => onEdit(field.id, event.target.value)}><option value="">{t("Chưa cung cấp")}</option>{field.options.map(option => <option key={option.value} value={option.value}>{t(option.label)}</option>)}</select> : field.multiline ? <textarea id={`saved-${field.id}`} rows={2} value={values[field.id] ?? ''} maxLength={field.maxLength} onChange={event => onEdit(field.id, event.target.value)} /> : <input id={`saved-${field.id}`} type={field.kind ?? 'text'} value={values[field.id] ?? ''} maxLength={field.maxLength} onChange={event => onEdit(field.id, event.target.value)} />}{field.hint && <small>{t(field.hint)}</small>}</div>)}</div></fieldset>)}</div>
    <div className={styles.saveBar}><p role="status">{busy ? t("Đang xử lý…") : problem ? t("Chưa có xác nhận lưu.") : saved ? t("Đã lưu hồ sơ.") : dirty ? t("Có thay đổi chưa lưu.") : t("Hồ sơ chỉ thay đổi khi bạn chọn lưu.")}</p><div><button type="button" disabled={busy || !dirty} onClick={onCancel}>{t("Hủy thay đổi")}</button><button type="submit" className={styles.primary} disabled={busy || !editable || !dirty}>{t("Lưu hồ sơ")}</button></div></div>
  </form>;
}
