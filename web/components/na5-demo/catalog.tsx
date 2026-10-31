'use client';
import { useState } from 'react';
import Link from 'next/link';
import { Search } from 'lucide-react';
import { PROCEDURE_TITLE } from './model';
import styles from './catalog.module.css';

// Exact candidate names/codes from Vincent's published candidates.yaml.
const catalog = [
  { code: '1.001146', name: PROCEDURE_TITLE, available: true },
  { code: '1.003326', name: 'Gia hạn tạm trú cho người nước ngoài (cấp trung ương)', available: false },
  { code: '1.003342', name: 'Cấp thị thực cho người nước ngoài tại Việt Nam (cấp trung ương)', available: false },
  { code: '1.000771', name: 'Gia hạn tạm trú cho người đã được cấp giấy miễn thị thực (cấp trung ương)', available: false },
];
const searchable = (value: string) => value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd');
export function Na5Catalog({ workspaceHref = '/demo/workspace' }: { workspaceHref?: string }) {
  const [query, setQuery] = useState('');
  const result = catalog.filter(item => searchable(`${item.code} ${item.name}`).includes(searchable(query.trim())));
  return <main id="main-content" className={styles.main}><p className="eyebrow">DANH MỤC TỪ VINCENT</p><h1>Chọn đúng thủ tục.</h1><p>Demo chỉ lọc danh mục đã nhận. Dịch vụ tìm kiếm và câu trả lời có nguồn chưa kết nối.</p><label htmlFor="catalog-query">Tìm tên hoặc mã thủ tục</label><div className={styles.search}><Search size={18} /><input id="catalog-query" type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="1.001146 hoặc gia hạn tạm trú" /></div><p role="status">{result.length} thủ tục trong danh mục</p><div className={styles.results}>{result.map(item => <article key={item.code} className={item.available ? styles.selected : ''}><div><span>{item.code}</span>{item.available && <b>NA5 · Bản điền thử</b>}</div><h2>{item.name}</h2>{item.available ? <><p>Mẫu 70/2026/TT-BCA trong bản giao nhận · trạng thái draft · tải bản điền đang khóa.</p><Link href={workspaceHref}>Mở bản nháp NA5 →</Link></> : <p>Danh mục tham chiếu. Chưa có quy trình điền tương ứng trong demo này.</p>}</article>)}</div>{!result.length && <button type="button" onClick={() => setQuery('')}>Xem lại danh mục</button>}<p className={styles.note}>Tên và mã lấy từ bản giao nhận 9386f428. Không có thủ tục đăng ký cư trú CT01 trong danh mục này.</p><Link className={styles.secondary} href="/demo/ct01">Thử nghiệm CT01 riêng, ngoài danh mục</Link></main>;
}
