'use client';
import { useLocale } from '@/components/ui/locale';

import { useEffect, useRef, useState } from 'react';
import { fieldLabel } from '@/components/guided-portal/state';
import type { Values, WorkflowSchema } from '@/components/na5-demo/model';
import { applyRows, prepareRows, proposalIssue, selectRow, type PrefillBinding, type PrefillClient, type PrefillContext, type PrefillRow } from './prefill-model';
import { ProfileError } from './api';
import { PrivacyNote } from './privacy-note';
import styles from './profile.module.css';

export function ConsentedPrefill({ client, context, draft, onFinish, onExpired, workflow }: { client: PrefillClient; context: PrefillContext; draft: Values; onFinish: (values: Values, copied: boolean, expectedRevision: number) => boolean; onExpired: () => void; workflow?: WorkflowSchema }) {
  const { t } = useLocale();
  const [phase, setPhase] = useState<'ask' | 'loading' | 'review' | 'checking' | 'stale' | 'unavailable'>('ask');
  const [applicant, setApplicant] = useState(false);
  const [documentConfirmed, setDocumentConfirmed] = useState(false);
  const [rows, setRows] = useState<PrefillRow[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [captured, setCaptured] = useState<PrefillBinding | null>(null);
  const pending = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const current = useRef({ context, draft }); current.current = { context, draft };
  const phaseRef = useRef(phase); phaseRef.current = phase;
  function invalidate() { generation.current += 1; pending.current?.abort(); setRows([]); setWarnings([]); setCaptured(null); setDocumentConfirmed(false); }
  function stale() { invalidate(); setPhase('stale'); }
  useEffect(() => {
    if (['loading', 'review', 'checking'].includes(phaseRef.current)) stale();
  }, [context.session, context.document, context.draftRevision]);
  useEffect(() => {
    const changed = () => { if (['loading', 'review', 'checking'].includes(phaseRef.current)) stale(); };
    window.addEventListener('hoso-profile-changed', changed);
    const channel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel('hoso-profile-revision');
    if (channel) channel.onmessage = changed;
    return () => { generation.current += 1; pending.current?.abort(); window.removeEventListener('hoso-profile-changed', changed); channel?.close(); };
  }, []);
  function fail(error: unknown) {
    invalidate();
    if (error instanceof Error && error.name === 'SessionExpired') onExpired();
    else setPhase(error instanceof ProfileError && error.status === 409 ? 'stale' : 'unavailable');
  }
  async function useProfile() {
    if (!applicant || phase === 'loading' || phase === 'checking') return;
    invalidate(); const attempt = generation.current; const snapshot = { ...current.current.context }; const values = { ...current.current.draft };
    const controller = new AbortController(); pending.current = controller; setPhase('loading');
    try {
      const source = await client.load(snapshot, values, controller.signal);
      if (attempt !== generation.current || controller.signal.aborted) return;
      const now = current.current.context;
      if (now.session !== snapshot.session || now.document !== snapshot.document || now.draftRevision !== snapshot.draftRevision) { stale(); return; }
      setRows(prepareRows(source, values, workflow)); setWarnings(source.warnings);
      setCaptured({ ...snapshot, profileId: source.profileId, profileRevision: source.revision }); setPhase('review');
    } catch (error) { if (attempt === generation.current && !controller.signal.aborted) fail(error); }
  }
  function manual() { const now = current.current; invalidate(); if (!onFinish({ ...now.draft }, false, now.context.draftRevision)) stale(); }
  async function apply() {
    if (!captured || phase !== 'review') return;
    const attempt = ++generation.current; const controller = new AbortController(); pending.current?.abort(); pending.current = controller; setPhase('checking');
    try {
      const latest = await client.check(controller.signal);
      if (attempt !== generation.current || controller.signal.aborted) return;
      const binding = { ...current.current.context, ...latest };
      const next = applyRows(rows, current.current.draft, captured, binding, documentConfirmed, workflow);
      if (!onFinish(next, true, captured.draftRevision)) { stale(); return; }
      invalidate();
    } catch (error) {
      if (attempt !== generation.current || controller.signal.aborted) return;
      if (error instanceof Error && error.message === 'Stale profile proposal') stale(); else fail(error);
    }
  }
  function editRow(id: string, value: string) {
    setRows(previous => previous.map(row => {
      if (row.id !== id) return row;
      const normalized = row.target === 'applicant_full_name' ? value.toUpperCase() : value;
      return { ...row, value: normalized, issue: proposalIssue(row.target, normalized, current.current.draft, workflow) };
    }));
  }
  function confirmDocument(confirmed: boolean) {
    setDocumentConfirmed(confirmed);
    setRows(previous => previous.map(row => row.requiresDocument ? { ...row, selected: confirmed && !row.locked && !row.issue } : row));
  }
  const selectable = rows.some(row => row.selected && !row.locked && !row.issue);
  const invalid = rows.some(row => row.selected && (Boolean(row.issue) || (row.requiresDocument && !documentConfirmed)));
  return <section className={styles.consent} aria-label={t("Dùng hồ sơ đã lưu")}>
    <h2>{t("Bạn muốn dùng hồ sơ đã lưu để điền tài liệu này?")}</h2>
    {phase === 'ask' && <><p>{t("Chỉ tải thông tin sau khi bạn đồng ý. Bạn sẽ xem, bỏ chọn hoặc sửa từng đề xuất trước khi áp dụng.")}</p><label><input type="checkbox" checked={applicant} onChange={event => setApplicant(event.target.checked)} />{t("Tôi là người đề nghị trong tài liệu này.")}</label><div className={styles.actions}><button type="button" className={styles.primary} disabled={!applicant} onClick={useProfile}>{t("Dùng hồ sơ")}</button><button type="button" onClick={manual}>{t("Không phải lúc này")}</button></div></>}
    {(phase === 'loading' || phase === 'checking') && <><p role="status">{phase === 'loading' ? t("Đang đọc hồ sơ của bạn…") : t("Đang kiểm tra phiên bản hồ sơ và bản nháp…")}</p><div className={styles.actions}><button type="button" onClick={manual}>{t("Tiếp tục nhập tay")}</button></div></>}
    {phase === 'review' && <><p>{t("Kiểm tra nguồn và giá trị sẽ điền. Câu trả lời đã có được giữ nguyên; hồ sơ đã lưu không thay đổi.")}</p>{rows.some(row => row.requiresDocument) && <label className={styles.documentConsent}><input type="checkbox" checked={documentConfirmed} onChange={event => confirmDocument(event.target.checked)} />{t("Tôi xác nhận hộ chiếu được hiển thị dưới đây là giấy tờ dùng cho lần đề nghị này.")}</label>}{rows.map(row => <div key={row.id} className={styles.proposal}><label><input type="checkbox" checked={row.selected} disabled={row.locked || (row.requiresDocument && !documentConfirmed)} onChange={event => setRows(previous => selectRow(previous, row.id, event.target.checked))} />{t(fieldLabel(row.target, workflow))}{row.target === 'contact' ? ` · ${t(row.sourceLabel)}` : ''}</label><p className={styles.source}>{t("Nguồn: ")}{t(row.sourceLabel)}<br />{t("Giá trị đã lưu: ")}{row.sourceValue}</p>{row.locked ? <p className={styles.locked}>{t("Đã có câu trả lời trên bản nháp: ")}{draft[row.target]}{t(". Không thay thế.")}</p> : <input aria-label={t(`Đề xuất ${fieldLabel(row.target, workflow)} · ${row.sourceLabel}`)} value={row.value} onChange={event => editRow(row.id, event.target.value)} autoComplete="off" />}{row.issue && <small>{t(row.issue)}</small>}</div>)}{warnings.map((warning, index) => <p key={index} className={styles.warning}>{t(warning)}</p>)}{!rows.length && <p>{t("Chưa có thông tin phù hợp để đề xuất. Bạn có thể tiếp tục nhập tay.")}</p>}<div className={styles.actions}><button type="button" className={styles.primary} disabled={!selectable || invalid} onClick={apply}>{t("Áp dụng các mục đã chọn")}</button><button type="button" onClick={manual}>{t("Tiếp tục nhập tay")}</button></div></>}
    {(phase === 'stale' || phase === 'unavailable') && <><p role="status">{phase === 'stale' ? t("Hồ sơ hoặc bản nháp đã thay đổi. Các đề xuất trước đã được hủy.") : t("Chưa có hồ sơ phù hợp hoặc chưa thể tải hồ sơ. Bản nháp được giữ nguyên.")}</p><div className={styles.actions}><button type="button" onClick={useProfile}>{t("Xem lại đề xuất")}</button><button type="button" onClick={manual}>{t("Tiếp tục nhập tay")}</button></div></>}
    <PrivacyNote />
  </section>;
}
