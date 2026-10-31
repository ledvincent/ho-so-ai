'use client';
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { ChevronDown, ChevronUp, Expand, FileText, Pencil, X } from 'lucide-react';
import pageData from '@/public/test-fixtures/na5/pages.json';
import { activeFields, editableFields, schema, type Values } from '@/components/na5-demo/model';
import { parts, position } from './document-layout';
import styles from './portal.module.css';
import paper from '@/components/na5-demo/workbench.module.css';

export function GuidedDocument({ values, activeId, onEdit, onManualMode }: { values: Values; activeId: string | null; onEdit: (id: string, value: string) => void; onManualMode: (open: boolean) => void }) {
  const [collapsed, setCollapsed] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [page, setPage] = useState(1);
  const [manualId, setManualId] = useState<string | null>(null);
  const [manualValue, setManualValue] = useState('');
  const viewport = useRef<HTMLDivElement>(null);
  const control = useRef<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | null>(null);
  const editable = editableFields(values);
  const manual = editable.find(field => field.id === manualId);
  const focus = editable.find(field => field.id === (manualId ?? activeId));
  const target = focus?.placements[0];
  const mapped = activeFields(values).flatMap(field => parts(field, values[field.id] ?? '').map(part => ({ ...part, field })));
  const crop = target && target.page === page ? { '--paper-top': `${Math.max(0, target.bbox[1] - 40) / pageData[page - 1].height * 100}%` } as CSSProperties : { '--paper-top': '12%' } as CSSProperties;
  useEffect(() => { onManualMode(Boolean(manual)); }, [manualId, Boolean(manual)]);
  useEffect(() => { if (target) setPage(target.page); }, [target?.page, activeId, manualId]);
  useEffect(() => { if (manual) { setManualValue(values[manual.id] ?? ''); control.current?.focus(); } }, [manualId]);
  function input() {
    if (!manual) return null;
    const props = { id: 'direct-value', value: manualValue, onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setManualValue(event.target.value) };
    if (manual.options) return <select {...props} ref={node => { control.current = node; }}><option value="">Chọn…</option>{manual.options.map(value => <option key={value}>{value}</option>)}</select>;
    if (manual.multiline) return <textarea {...props} rows={2} ref={node => { control.current = node; }} />;
    return <input {...props} ref={node => { control.current = node; }} autoComplete="off" placeholder={manual.type === 'date' ? 'YYYY-MM-DD' : ''} />;
  }
  return <section className={`${styles.document} ${expanded ? styles.documentExpanded : ''}`} aria-label="Bản nháp NA5">
    <header><div><FileText size={17} /><b>NA5</b><span>1.001146 · Bản nháp</span></div><div><button type="button" onClick={() => { setExpanded(!expanded); setCollapsed(false); }} aria-label={expanded ? 'Thu nhỏ tài liệu' : 'Mở rộng tài liệu'}><Expand size={15} /></button><button type="button" onClick={() => setCollapsed(!collapsed)} aria-expanded={!collapsed} aria-label={collapsed ? 'Hiện tài liệu' : 'Ẩn tài liệu'}>{collapsed ? <ChevronDown size={17} /> : <ChevronUp size={17} />}</button></div></header>
    {!collapsed && <><div className={styles.paperViewport} ref={viewport} style={crop}><div className={`${paper.paper} ${styles.guidedPaper}`}><img src={`/test-fixtures/na5/page-${page}.png`} alt={`NA5 trang ${page} · bản nháp đang chờ duyệt`} />{mapped.filter(part => part.placement.page === page).map((part, index) => <span key={`${part.field.id}-${index}`} className={paper.value} style={{ ...position(part.placement), fontSize: `${part.size / pageData[page - 1].width * 100}cqw` }}>{part.overflow ? '↗' : part.text}</span>)}{activeFields(values).flatMap(field => field.placements.filter(p => p.page === page).map((placement, index) => <button key={`${field.id}-${index}`} type="button" className={`${paper.overlay} ${field.id === (manualId ?? activeId) ? paper.active : ''}`} style={position(placement)} disabled={Object.hasOwn(schema.fixed_values, field.id)} aria-label={`Sửa ${field.label} ${index + 1}`} onClick={() => setManualId(field.id)} />))}</div></div>
      <footer><span>Đang chờ duyệt mẫu · Chữ ký giữ trống</span><button type="button" onClick={() => { setManualId(activeId ?? editable[0].id); }}><Pencil size={12} />Sửa trực tiếp</button>{expanded && <div>{pageData.map(item => <button type="button" key={item.page} aria-pressed={page === item.page} onClick={() => setPage(item.page)}>{item.page}</button>)}</div>}</footer></>}
    {manual && <form className={styles.directEditor} onSubmit={event => { event.preventDefault(); onEdit(manual.id, manualValue); setManualId(null); }}><div><label htmlFor="direct-field">Sửa mục</label><button type="button" aria-label="Đóng sửa trực tiếp" onClick={() => setManualId(null)}><X size={17} /></button></div><select id="direct-field" value={manual.id} onChange={event => setManualId(event.target.value)}>{editable.map(field => <option key={field.id} value={field.id}>{field.label}</option>)}</select><label htmlFor="direct-value">{manual.label}</label>{input()}<div><small>Chỉ sửa bản nháp này. Không tự lưu hồ sơ.</small><button type="submit">Áp dụng</button></div></form>}
  </section>;
}
