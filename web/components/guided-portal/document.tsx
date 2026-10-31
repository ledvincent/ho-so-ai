'use client';
import { useLocale } from '@/components/ui/locale';

import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Expand, FileText, Pencil, X } from 'lucide-react';
import pageData from '@/public/test-fixtures/na5/pages.json';
import { activeFields, editableFields, schema as defaultSchema, type Values } from '@/components/na5-demo/model';
import type { DocumentPresentation } from '@/components/procedure-chat/document-model';
import { NA5_FORM } from '@/components/procedure-chat/model';
import { parts, position } from './document-layout';
import styles from './portal.module.css';
import paper from '@/components/na5-demo/workbench.module.css';

export function GuidedDocument({ values, activeId, onEdit, onManualMode, workflow }: { values: Values; activeId: string | null; onEdit: (id: string, value: string) => void; onManualMode: (open: boolean) => void; workflow?: DocumentPresentation }) {
  const { t } = useLocale();
  const schema = workflow?.schema ?? defaultSchema;
  const formId = workflow?.action.form_id ?? 'NA5';
  const pages = workflow?.pages ?? pageData.map((_, index) => ({ pageNumber: index + 1, imageUrl: `/test-fixtures/na5/page-${index + 1}.png` }));
  // The reviewed NA5 geometry belongs only to this original. Other documents use
  // their own pages and dynamic manual fields, without borrowing NA5 overlays.
  const knownGeometry = !workflow || (workflow.action.document_id === 'na5-provincial-stay-extension' && workflow.action.template_sha256 === NA5_FORM && pages.length === pageData.length);
  const [imageRatio, setImageRatio] = useState(1);
  const [collapsed, setCollapsed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [page, setPage] = useState(1);
  const [manualId, setManualId] = useState<string | null>(null);
  const [manualValue, setManualValue] = useState('');
  const [zoom, setZoom] = useState('page');
  const [paperWidth, setPaperWidth] = useState(240);
  const [screen, setScreen] = useState({ height: 1000, top: 0 });
  const compact = screen.height < 560;
  const visible = !collapsed && (!compact || expanded);
  const viewport = useRef<HTMLDivElement>(null);
  const control = useRef<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null>(null);
  const editable = editableFields(values, schema);
  const manual = editable.find(field => field.id === manualId);
  const focus = editable.find(field => field.id === (manualId ?? activeId));
  const target = focus?.placements[0];
  const mapped = knownGeometry ? activeFields(values, schema).flatMap(field => parts(field, values[field.id] ?? '').map(part => ({ ...part, field }))) : [];
  useEffect(() => {
    const viewport = window.visualViewport;
    const resize = () => setScreen({ height: viewport?.height ?? window.innerHeight, top: viewport?.offsetTop ?? 0 });
    resize(); viewport?.addEventListener('resize', resize); viewport?.addEventListener('scroll', resize);
    return () => { viewport?.removeEventListener('resize', resize); viewport?.removeEventListener('scroll', resize); };
  }, []);
  useEffect(() => { onManualMode(Boolean(manual)); }, [manualId, Boolean(manual)]);
  useEffect(() => {
    const area = viewport.current; if (!area) return;
    function resize() {
      if (!area) return; const width = Math.max(60, area.clientWidth - 24); const height = Math.max(60, area.clientHeight - 24);
      const ratio = knownGeometry ? pageData[page - 1].width / pageData[page - 1].height : imageRatio;
      setPaperWidth(zoom === 'page' ? Math.min(width, height * ratio) : width * (zoom === 'width' ? 1 : Number(zoom)));
    }
    resize(); const observer = new ResizeObserver(resize); observer.observe(area);
    return () => observer.disconnect();
  }, [zoom, expanded, visible, Boolean(manual), page, imageRatio]);
  useEffect(() => { if (manual) { setManualValue(values[manual.id] ?? ''); control.current?.focus(); } }, [manualId]);
  function input() {
    if (!manual) return null;
    const props = { id: 'direct-value', value: manualValue, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setManualValue(event.target.value) };
    if (manual.options) return <select {...props} ref={node => { control.current = node; }}><option value="">{t("Chọn…")}</option>{manual.options.map(value => <option key={value} value={value}>{t(value)}</option>)}</select>;
    if (manual.multiline) return <textarea {...props} rows={2} ref={node => { control.current = node; }} />;
    return <input {...props} ref={node => { control.current = node; }} autoComplete="off" placeholder={manual.type === 'date' ? 'YYYY-MM-DD' : ''} />;
  }
  return <section className={`${styles.document} ${expanded ? styles.documentExpanded : ''}`} style={expanded ? { top: screen.top + 7, height: screen.height - 14, bottom: 'auto' } : undefined} aria-label={`${t("Bản nháp")} ${formId}`}>
    <header><div><FileText size={17} /><b>{formId}</b><span>{schema.procedure_code} · {t("Bản nháp")}</span></div><div><button type="button" onClick={() => { setExpanded(!expanded); setCollapsed(false); }} aria-label={expanded ? t("Thu nhỏ tài liệu") : t("Mở rộng tài liệu")}><Expand size={15} /></button><button type="button" onClick={() => { if (visible) { setCollapsed(true); setExpanded(false); } else { setCollapsed(false); if (compact) setExpanded(true); } }} aria-expanded={visible} aria-label={collapsed ? t("Hiện tài liệu") : t("Ẩn tài liệu")}>{!visible ? <ChevronDown size={17} /> : <ChevronUp size={17} />}</button></div></header>
    {visible && <><div className={styles.viewerControls}><div><button type="button" aria-label={t("Trang trước")} disabled={page === 1} onClick={() => setPage(page - 1)}><ChevronLeft size={15} /></button><span aria-live="polite">{page} {t(" / ")}{pages.length}</span><button type="button" aria-label={t("Trang sau")} disabled={page === pages.length} onClick={() => setPage(page + 1)}><ChevronRight size={15} /></button></div><label>{t("Thu phóng")}<select value={zoom} onChange={event => setZoom(event.target.value)}><option value="page">{t("Vừa trang")}</option><option value="width">{t("Vừa chiều rộng")}</option><option value="1.5">{t("150%")}</option><option value="2">{t("200%")}</option></select></label>{target && <button type="button" onClick={() => setPage(target.page)}>{t("Đến mục đang điền")}</button>}</div><div className={styles.paperViewport} ref={viewport}><div className={`${paper.paper} ${styles.guidedPaper}`} style={{ '--page-width': `${paperWidth}px` } as CSSProperties}><img src={pages[page - 1].imageUrl} onLoad={event => { if (!knownGeometry) setImageRatio(event.currentTarget.naturalWidth / event.currentTarget.naturalHeight); }} alt={`${formId} · ${t("Trang")} ${page} · ${t("Bản nháp, chờ duyệt")}`} />{mapped.filter(part => part.placement.page === page).map((part, index) => <span key={`${part.field.id}-${index}`} className={paper.value} style={{ ...position(part.placement), fontSize: `${part.size / pageData[page - 1].width * 100}cqw` }}>{part.overflow ? t("↗") : part.text}</span>)}{(knownGeometry ? activeFields(values, schema) : []).flatMap(field => field.placements.filter(p => p.page === page).map((placement, index) => <button key={`${field.id}-${index}`} type="button" className={`${paper.overlay} ${field.id === (manualId ?? activeId) ? paper.active : ''}`} style={position(placement)} disabled={Object.hasOwn(schema.fixed_values, field.id)} aria-label={t(`Sửa ${field.label} ${index + 1}`)} onClick={() => setManualId(field.id)} />))}</div></div>
      <footer><span>{t("Đang chờ duyệt mẫu · Chữ ký giữ trống")}</span><button type="button" disabled={!editable.length} onClick={() => { setManualId(activeId ?? editable[0]?.id ?? null); }}><Pencil size={12} />{t("Sửa trực tiếp")}</button></footer></>}
    {manual && <form className={styles.directEditor} onSubmit={event => { event.preventDefault(); onEdit(manual.id, manualValue); setManualId(null); }}><div><label htmlFor="direct-field">{t("Sửa mục")}</label><button type="button" aria-label={t("Đóng sửa trực tiếp")} onClick={() => setManualId(null)}><X size={17} /></button></div><select id="direct-field" value={manual.id} onChange={event => setManualId(event.target.value)}>{editable.map(field => <option key={field.id} value={field.id}>{field.label}</option>)}</select><label htmlFor="direct-value">{t(manual.label)}</label>{input()}<div><small>{t("Chỉ sửa bản nháp này. Không tự lưu hồ sơ.")}</small><button type="submit">{t("Áp dụng")}</button></div></form>}
  </section>;
}
