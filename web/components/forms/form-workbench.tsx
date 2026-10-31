'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowDownToLine, ArrowLeft, ArrowRight, Check, ChevronRight, CircleCheck, FileText, LoaderCircle, LockKeyhole, PenLine, RefreshCw, ShieldCheck, UserRound } from 'lucide-react';
import { EMPTY_PROFILE, type ProfileFields, type ProfileRecord } from '@/lib/contracts';
import { canDownload, captureRequest, clearDraft, editDraft, isCurrent, newDraft, prefillDraft, validateProfile, type Draft, type FieldId } from '@/lib/forms/draft';
import styles from './form-workbench.module.css';

type Props = { accountState: 'unconfigured' | 'signed-out' | 'signed-in'; accountKey?: string };
const fields: { id: FieldId; label: string; placeholder: string; type?: string; wide?: boolean; hint?: string }[] = [
  { id: 'full_name', label: 'Full name', placeholder: 'As shown on your identity document', wide: true },
  { id: 'date_of_birth', label: 'Date of birth', placeholder: '', type: 'date' },
  { id: 'nationality', label: 'Nationality', placeholder: 'Enter your nationality' },
  { id: 'address', label: 'Residential address', placeholder: 'House number, street, ward and city', wide: true, hint: 'Long addresses wrap onto the next available line.' },
  { id: 'phone_number', label: 'Phone number', placeholder: '+84 …', type: 'tel' },
  { id: 'email', label: 'Email address', placeholder: 'you@example.com', type: 'email' },
];
const sample: ProfileFields = { full_name: 'Nguyễn Văn Mẫu', date_of_birth: '1994-05-16', nationality: 'Việt Nam', address: '123 Đường Mẫu, Phường Minh Họa, Thành phố Ví Dụ', phone_number: '+84 000 000 000', email: 'sample@example.test' };

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
  const errors = { ...validateProfile(draft.values), ...renderErrors };
  const valid = Object.keys(errors).length === 0;
  const filled = Object.values(draft.values).filter((value) => value?.trim()).length;

  function removePreview() {
    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    previewUrl.current = null; setPreview(null);
  }
  function update(next: Draft) {
    generation.current += 1; pending.current?.abort(); pending.current = null;
    current.current = next; setDraft(next); removePreview(); setBusy(null); setFailure(''); setNotice(''); setRenderErrors({});
  }
  function edit(id: FieldId, value: string) { update(editDraft(current.current, id, value)); }
  useEffect(() => {
    if (previousAccount.current !== accountKey) {
      previousAccount.current = accountKey;
      update(clearDraft(current.current));
    }
  }, [accountKey]); // A changed authenticated identity clears the old user's draft.
  useEffect(() => {
    const clear = () => {
      generation.current += 1; pending.current?.abort(); removePreview();
      const next = clearDraft(current.current); current.current = next; setDraft(next); setBusy(null);
    };
    window.addEventListener('pagehide', clear);
    return () => { generation.current += 1; window.removeEventListener('pagehide', clear); pending.current?.abort(); if (previewUrl.current) URL.revokeObjectURL(previewUrl.current); };
  }, []);

  async function loadAccount() {
    if (accountState !== 'signed-in') return;
    const attempt = ++generation.current; const revision = current.current.revision;
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    setBusy('profile'); setFailure(''); setNotice('');
    try {
      const response = await fetch('/api/profile', { cache: 'no-store', signal: controller.signal });
      if (attempt !== generation.current || revision !== current.current.revision) return;
      if (!response.ok) {
        setFailure(response.status === 501 ? 'Saved profiles are not connected yet. You can enter your details by hand.' : response.status === 404 ? 'Your account has no saved profile yet. Enter your details by hand.' : 'Your saved details could not be loaded. Please sign in again or enter them by hand.');
        return;
      }
      const profile: ProfileRecord = await response.json();
      if (attempt !== generation.current || revision !== current.current.revision) return;
      update(prefillDraft(current.current, { ...EMPTY_PROFILE, ...profile.fields }));
      setNotice('Saved details copied. Changes here apply to this document; your account profile is unchanged.');
    } catch (error) { if (!(error instanceof DOMException && error.name === 'AbortError') && attempt === generation.current) setFailure('Saved details are unavailable. Your current entries have been kept.'); }
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
          setRenderErrors({ [field]: code === 'text_overflow' ? 'This value is too long for the document. Shorten it; it will not be clipped.' : 'Check this value before preparing the document.' });
        }
        if (response.status === 409) {
          removePreview(); const next = { ...current.current, previewRevision: null, acknowledged: false };
          current.current = next; setDraft(next);
        }
        setFailure(code === 'text_overflow' ? 'Some text is too long for the document. Shorten it before previewing; nothing has been clipped.' : code === 'unsupported_glyph' ? 'A character cannot be rendered in the document font. Review the highlighted information.' : response.status === 404 || response.status === 503 ? 'The local document renderer is not available. Start the API with synthetic forms enabled.' : response.status === 409 ? 'The form version changed. Refresh your preview and check it again.' : 'The document could not be prepared. Check your entries and try again.');
        return;
      }
      const blob = await response.blob();
      if (attempt !== generation.current || !isCurrent(current.current, snapshot)) return;
      if (format === 'preview') {
        removePreview(); const url = URL.createObjectURL(blob); previewUrl.current = url; setPreview(url);
        const next = { ...current.current, previewRevision: snapshot.revision, acknowledged: false };
        current.current = next; setDraft(next); setNotice('Preview updated. Check the document before downloading.');
      } else {
        const url = URL.createObjectURL(blob); const anchor = document.createElement('a');
        anchor.href = url; anchor.download = 'ho-so-ai-synthetic-review.pdf'; anchor.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000); setNotice('Synthetic PDF downloaded. No information has been saved to your account.');
      }
    } catch (error) { if (!(error instanceof DOMException && error.name === 'AbortError') && attempt === generation.current) setFailure('The document service could not be reached. Your entries are still in this tab.'); }
    finally { if (attempt === generation.current) setBusy(null); }
  }

  return <main className={styles.main}>
    <div className={styles.breadcrumb}><Link href="/">Home</Link><ChevronRight size={13} /><span>Prepare a form</span></div>
    <div className={styles.heading}><div><p className="eyebrow">A little preparation goes a long way</p><h1>Your details.<br className={styles.mobileBreak} /> Clearly on paper.</h1><p>Enter your information, check the preview, then download your document.</p></div><span className={styles.draftBadge}><span /> Draft · only in this tab</span></div>
    <div className={styles.demoNotice}><FileText size={17} /><span><strong>Synthetic form preview.</strong> Use sample data only. Official CT01 export will be enabled after its exact template is reviewed.</span><button type="button" onClick={() => update({ ...prefillDraft(current.current, sample), source: 'manual' })}>Load sample <ArrowRight size={13} /></button></div>
    <div className={styles.columns}>
      <section className={styles.editor} aria-labelledby="details-title">
        <div className={styles.sectionHeading}><span className={styles.step}>01</span><div><h2 id="details-title">Your information</h2><p>Choose how you would like to start.</p></div><span className={styles.count}>{filled} / 6 fields</span></div>
        <div className={styles.sourceChoices}>
          <button type="button" className={draft.source === 'manual' ? styles.selected : ''} onClick={() => { if (draft.source !== 'manual') update({ ...current.current, source: 'manual', revision: current.current.revision + 1, acknowledged: false, previewRevision: null }); }}><PenLine size={19} /><span><strong>Enter by hand</strong><small>Fill in your details below</small></span>{draft.source === 'manual' && <CircleCheck size={16} />}</button>
          <button type="button" className={draft.source === 'account' ? styles.selected : ''} onClick={loadAccount} disabled={accountState !== 'signed-in' || busy === 'profile'}><UserRound size={19} /><span><strong>Use my account</strong><small>{busy === 'profile' ? 'Loading saved details…' : 'Start from your saved profile'}</small></span>{draft.source === 'account' ? <CircleCheck size={16} /> : <LockKeyhole size={14} />}</button>
        </div>
        {accountState !== 'signed-in' && <p className={styles.accountHint}>{accountState === 'unconfigured' ? 'Account prefill is ready to connect once Clerk and saved profiles are configured.' : <><Link href="/sign-in">Sign in</Link> to use your saved information.</>}</p>}
        {draft.source === 'account' && <p className={styles.accountHint}>You can edit the copied values. Your saved account profile will stay unchanged.</p>}
        <div className={styles.fields}>{fields.map((field) => <div key={field.id} className={field.wide ? styles.wide : ''}>
          <label htmlFor={field.id}>{field.label}</label>
          {field.id === 'address' ? <textarea id={field.id} rows={3} value={draft.values[field.id] ?? ''} onChange={(event) => edit(field.id, event.target.value)} placeholder={field.placeholder} autoComplete="off" aria-invalid={Boolean(errors[field.id])} aria-describedby={`${field.id}-hint`} /> : <input id={field.id} type={field.type ?? 'text'} value={draft.values[field.id] ?? ''} onChange={(event) => edit(field.id, event.target.value)} placeholder={field.placeholder} autoComplete="off" aria-invalid={Boolean(errors[field.id])} aria-describedby={`${field.id}-hint`} />}
          <p id={`${field.id}-hint`} className={errors[field.id] ? styles.fieldError : styles.fieldHint}>{errors[field.id] ?? field.hint ?? ''}</p>
        </div>)}</div>
        <div className={styles.editorBottom}><button className={styles.clear} type="button" onClick={() => update(clearDraft(current.current))}>Clear details</button><button className="button primary" type="button" onClick={() => renderDocument('preview')} disabled={!valid || busy !== null}>{busy === 'preview' ? <LoaderCircle className={styles.spin} size={16} /> : <RefreshCw size={16} />}Update preview</button></div>
        <div className={styles.privacy}><ShieldCheck size={18} /><p>Your entries stay in this tab until you request a preview or PDF. This demo renderer processes them temporarily and does not save a profile.</p></div>
      </section>
      <section className={styles.review} aria-labelledby="review-title">
        <div className={styles.sectionHeading}><span className={styles.step}>02</span><div><h2 id="review-title">Review your document</h2><p>What you see is what goes into the PDF.</p></div></div>
        <div className={styles.previewBar}><span><FileText size={14} /> Personal details · A4</span><span>{preview ? 'Preview ready' : 'Awaiting preview'}</span></div>
        <div className={styles.paperArea}>{preview ? <img src={preview} alt="Synthetic document preview showing the current entered details, with text above the dotted lines." className={styles.document} /> : <div className={styles.placeholderPaper}><div className={styles.paperLogo}>h.</div><p className={styles.paperEyebrow}>SYNTHETIC REVIEW COPY</p><h3>Personal information</h3><div className={styles.paperDivider} />{['Full name', 'Date of birth', 'Nationality', 'Residential address', 'Contact details'].map((label) => <div className={styles.paperField} key={label}><span>{label}</span><div /></div>)}<p className={styles.paperFoot}>Your preview will appear here after you enter your details.</p></div>}</div>
        <div className={styles.reviewBottom}><label className={styles.confirm}><input type="checkbox" checked={draft.acknowledged} disabled={draft.previewRevision !== draft.revision || busy !== null} onChange={(event) => { const next = { ...current.current, acknowledged: event.target.checked }; current.current = next; setDraft(next); }} /><span>I have checked the information in this preview.</span></label><button className={`button primary ${styles.download}`} type="button" onClick={() => renderDocument('pdf')} disabled={!canDownload(draft) || busy !== null}>{busy === 'pdf' ? <LoaderCircle className={styles.spin} size={17} /> : <ArrowDownToLine size={17} />}Download PDF<ArrowRight size={16} /></button><p className={styles.downloadHint}><Check size={12} /> Edits always require a fresh preview.</p></div>
      </section>
    </div>
    <div className={styles.feedback} aria-live="polite" role="status">{failure ? <p className={styles.failure}>{failure}</p> : notice ? <p><CircleCheck size={16} />{notice}</p> : null}</div>
    <Link href="/" className={styles.back}><ArrowLeft size={14} /> Back to home</Link>
  </main>;
}
