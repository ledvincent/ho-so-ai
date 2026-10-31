'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowUp, Check, MessageSquare, RotateCcw } from 'lucide-react';
import type { ProfileFields } from '@/lib/contracts';
import type { FieldId } from '@/lib/forms/draft';
import { BrandMark } from '@/components/ui/brand';
import { CHAT_FIELDS, nextChatField, resolveDemoAnswer } from './demo-answer';
import styles from './draft-chat.module.css';

export type DraftChatProps = {
  values: ProfileFields;
  onApply: (field: FieldId, value: string) => void;
  resetKey: number;
  activeField: FieldId | null;
  onSelectField: (field: FieldId) => void;
  minimized?: boolean;
};

export function DraftChat({ values, onApply, resetKey, activeField, onSelectField, minimized = false }: DraftChatProps) {
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState<{ kind: 'apply' | 'clarify'; message: string } | null>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const selected = CHAT_FIELDS.find((item) => item.field === activeField);
  const complete = CHAT_FIELDS.every(item => values[item.field]?.trim());

  useEffect(() => { setAnswer(''); setFeedback(null); }, [resetKey]);
  useEffect(() => { setAnswer(''); setFeedback(previous => previous?.kind === 'clarify' ? null : previous); }, [activeField]);

  function select(field: FieldId) {
    setAnswer(''); setFeedback(null); onSelectField(field);
    composer.current?.focus({ preventScroll: true });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const result = resolveDemoAnswer(activeField, answer);
    if (result.kind === 'clarify') { setFeedback(result); return; }
    onApply(result.field, result.value);
    const label = CHAT_FIELDS.find((item) => item.field === result.field)!.label;
    // Confirm only the field name; raw answers are not copied into a transcript.
    setFeedback({ kind: 'apply', message: `Đã cập nhật “${label}” trên bản nháp. Bạn có thể bấm vào mục đó để sửa lại.` });
    setAnswer('');
    onSelectField(nextChatField({ ...values, [result.field]: result.value }, result.field));
  }

  return <section className={styles.chat} aria-labelledby="draft-chat-heading">
    <header className={styles.heading}>
      <span className={styles.avatar}><BrandMark /></span>
      <div><h2 id="draft-chat-heading">Điền cùng Hồ Sơ AI</h2><p>Trò chuyện minh họa · không dùng AI thực</p></div>
    </header>
    <div className={styles.conversation}>
      <div className={styles.fieldGroup} role="group" aria-label="Chọn mục cần điền">
        {CHAT_FIELDS.map((item) => <button key={item.field} type="button" aria-pressed={item.field === activeField} onClick={() => select(item.field)} className={item.field === activeField ? styles.active : ''}>
          {values[item.field]?.trim() && <Check size={12} aria-hidden="true" />}<span>{item.label}</span>
        </button>)}
      </div>
      <div className={styles.prompt} aria-live="polite"><span className={styles.promptLabel}>Hồ Sơ AI</span><p>{selected?.prompt ?? 'Bạn muốn bắt đầu ở mục nào? Chọn một mục trên văn bản hoặc dùng các nút phía trên.'}</p></div>
      {feedback && <div className={`${styles.feedback} ${feedback.kind === 'clarify' ? styles.clarification : ''}`} role="status" aria-live="polite">
        {feedback.kind === 'apply' ? <Check size={15} aria-hidden="true" /> : <RotateCcw size={15} aria-hidden="true" />}<p>{feedback.message}</p>
      </div>}
      {selected && <dl className={styles.currentValue}><dt>Đang sửa: {selected.label}</dt><dd>{values[selected.field] || <span>Chưa điền</span>}</dd></dl>}
      <p className={styles.draftNote}>Thay đổi cập nhật ngay bản nháp. Hồ sơ tài khoản đã lưu không thay đổi.</p>
      {complete && <p className={styles.completed}>Đã có thông tin ở cả 6 mục. <a href="#document-review">Rà soát bản PDF trước khi tải xuống →</a></p>}
    </div>
    <form className={`${styles.composer} ${minimized ? styles.minimized : ''}`} onSubmit={submit}>
      {minimized && <button type="button" className={styles.resume} onClick={() => onSelectField(activeField ?? 'full_name')}>Trở lại ô trả lời <MessageSquare size={15} aria-hidden="true" /></button>}
      <label htmlFor="draft-chat-answer">{selected ? `Nhập ${selected.label.toLocaleLowerCase('vi')}` : 'Chọn một mục để bắt đầu'}</label>
      <div className={styles.inputRow}><textarea ref={composer} id="draft-chat-answer" rows={2} value={answer} onChange={(event) => setAnswer(event.target.value)} disabled={!selected} placeholder={selected?.placeholder ?? 'Chọn mục cần điền ở phía trên'} aria-describedby="draft-chat-help" /><button type="submit" disabled={!selected || !answer.trim()} aria-label="Điền câu trả lời vào bản nháp"><ArrowUp size={19} aria-hidden="true" /></button></div>
      <p id="draft-chat-help">Giữ nguyên nội dung bạn gửi. Có thể sửa trực tiếp trên văn bản.</p>
    </form>
  </section>;
}
