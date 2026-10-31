'use client';

import { useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BookOpen, ChevronDown, FileDown, FileText, Info, Search, UserRound, X } from 'lucide-react';
import styles from './research.module.css';

// Presentation-only fixtures about this app's flow. These are not procedure
// records or a retrieval contract. Vincent's search integration remains separate.
const demoGuides = [
  {
    id: 'profile',
    title: 'Chuẩn bị hồ sơ',
    topic: 'THÔNG TIN DÙNG LẠI',
    description: 'Chuẩn bị thông tin tài khoản để có thể sao chép vào một bản nháp khi cần.',
    keywords: 'tai khoan thong tin ca nhan luu dien tay',
    icon: UserRound,
    steps: [
      'Mở hồ sơ và đăng nhập nếu tính năng tài khoản đã sẵn sàng.',
      'Điền thông tin mẫu, chọn “Lưu hồ sơ” và đợi xác nhận trước khi chuyển sang biểu mẫu.',
      'Bạn cũng có thể nhập tay trong biểu mẫu. Thay đổi chưa lưu trong hồ sơ không được chuyển theo.',
    ],
    href: '/portal',
    action: 'Mở hồ sơ',
  },
  {
    id: 'review',
    title: 'Rà soát bản nháp',
    topic: 'BIỂU MẪU THỬ NGHIỆM',
    description: 'Kiểm tra nội dung vừa nhập và bản xem trước của biểu mẫu.',
    keywords: 'kiem tra bieu mau chinh sua xem truoc thong tin',
    icon: FileText,
    steps: [
      'Nhập tay hoặc chủ động chọn sao chép hồ sơ đã lưu vào biểu mẫu.',
      'Chỉnh sửa bản nháp bằng dữ liệu giả lập rồi tạo bản xem trước để đối chiếu.',
      'Nếu tiếp tục chỉnh sửa, hãy cập nhật bản xem trước và rà soát lại. Chỉnh bản nháp không tự cập nhật hồ sơ.',
    ],
    href: '/forms/demo#document-review',
    action: 'Mở phần rà soát',
  },
  {
    id: 'download',
    title: 'Tải PDF thử nghiệm',
    topic: 'BẢN SAO ĐỂ KIỂM TRA',
    description: 'Tải bản PDF giả lập sau khi xem lại và xác nhận nội dung bản nháp.',
    keywords: 'tai xuong tep file xuat pdf gia lap mau',
    icon: FileDown,
    steps: [
      'Tạo bản xem trước từ dữ liệu mẫu và kiểm tra các thông tin được hiển thị.',
      'Xác nhận đã rà soát rồi chọn tải PDF. File chỉ được tạo khi dịch vụ thử nghiệm khả dụng.',
      'PDF này là tài liệu giả lập. Tải file không gửi hồ sơ đến cơ quan tiếp nhận.',
    ],
    href: '/forms/demo#document-review',
    action: 'Mở bản nháp và PDF',
  },
] as const;

function searchText(value: string) {
  return value.toLocaleLowerCase('vi').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd');
}

export default function Research() {
  const [query, setQuery] = useState('');
  const queryInput = useRef<HTMLInputElement>(null);
  function clearQuery() {
    setQuery('');
    queryInput.current?.focus();
  }
  const words = searchText(query.trim()).split(/\s+/).filter(Boolean);
  const results = demoGuides.filter(guide => {
    const content = searchText(`${guide.title} ${guide.topic} ${guide.description} ${guide.keywords} ${guide.steps.join(' ')}`);
    return words.every(word => content.includes(word));
  });

  return <main id="main-content" lang="vi" className={styles.shell}>
    <header className={styles.heading}>
      <p className={styles.eyebrow}>TRA CỨU THỦ CÔNG</p>
      <h1>Tìm đúng bước tiếp theo.</h1>
      <p>Chọn một hướng dẫn để làm quen với hồ sơ, bản nháp và PDF trong ứng dụng.</p>
    </header>

    <section className={styles.demoNotice} aria-labelledby="demo-title">
      <Info size={19} aria-hidden="true" />
      <div><h2 id="demo-title">Bản minh họa · Tra cứu nguồn chưa kết nối</h2><p>Hiện chỉ có ba hướng dẫn mẫu về cách dùng ứng dụng. Đây không phải kết quả tra cứu thủ tục hoặc thông tin từ nguồn chính thức.</p></div>
    </section>

    <div className={styles.layout}>
      <section className={styles.guideSection} aria-labelledby="guides-title">
        <div className={styles.sectionHeading}><h2 id="guides-title">Hướng dẫn mẫu</h2><span>CHỈ LỌC NỘI DUNG TRÊN TRANG</span></div>
        <div className={styles.searchArea}>
          <label htmlFor="guide-query">Bạn muốn tìm bước nào?</label>
          <div className={styles.searchBox}>
            <Search size={19} aria-hidden="true" />
            <input ref={queryInput} id="guide-query" type="search" value={query} onChange={event => setQuery(event.target.value)} maxLength={120} placeholder="Ví dụ: hồ sơ, bản nháp, PDF" aria-controls="guide-results" aria-describedby="search-note" />
            {query && <button className={styles.clearButton} type="button" onClick={clearQuery} aria-label="Xóa nội dung lọc"><X size={17} aria-hidden="true" /></button>}
          </div>
          <p id="search-note">Lọc ngay trên trang; nội dung tìm kiếm không được gửi tới dịch vụ tra cứu.</p>
        </div>
        <p className={styles.resultCount} role="status" aria-live="polite">{results.length} hướng dẫn mẫu{query.trim() ? ' phù hợp' : ''}</p>
        <div id="guide-results" className={styles.results}>
          {results.map(guide => {
            const Icon = guide.icon;
            return <article className={styles.guideCard} key={guide.id} aria-labelledby={`guide-${guide.id}`}>
              <div className={styles.guideHeading}><span className={styles.guideIcon}><Icon size={21} aria-hidden="true" /></span><div><p className={styles.topic}>{guide.topic}</p><h3 id={`guide-${guide.id}`}>{guide.title}</h3></div></div>
              <p className={styles.description}>{guide.description}</p>
              <details className={styles.details}>
                <summary>Xem các bước minh họa <ChevronDown size={16} aria-hidden="true" /></summary>
                <ol>{guide.steps.map(step => <li key={step}>{step}</li>)}</ol>
              </details>
              <Link className={styles.guideLink} href={guide.href} prefetch={false}>{guide.action}<ArrowRight size={16} aria-hidden="true" /></Link>
            </article>;
          })}
          {results.length === 0 && <div className={styles.empty}>
            <Search size={26} aria-hidden="true" /><h3>Chưa có hướng dẫn mẫu phù hợp</h3><p>Thử “hồ sơ”, “bản nháp” hoặc “PDF”. Bộ lọc này chỉ tìm trong ba hướng dẫn minh họa ở trên.</p><button className={styles.secondary} type="button" onClick={clearQuery}>Xem tất cả hướng dẫn mẫu</button>
          </div>}
        </div>
      </section>

      <aside className={styles.sidebar}>
        <section className={styles.sourceCard} aria-labelledby="source-title">
          <span className={styles.sourceIcon}><BookOpen size={24} aria-hidden="true" /></span>
          <span className={styles.unavailable}>Chưa kết nối</span>
          <h2 id="source-title">Tra cứu từ nguồn</h2>
          <p>Dịch vụ tìm kiếm và dữ liệu nguồn chưa được kết nối tại đây. Chưa có kết quả hoặc liên kết nguồn để đối chiếu.</p>
          <p className={styles.sourceNote}>Các thẻ hướng dẫn chỉ mô tả thao tác trong ứng dụng. Chúng không cung cấp yêu cầu, điều kiện hoặc hướng dẫn pháp lý.</p>
        </section>
        <section className={styles.nextCard}>
          <p className={styles.eyebrow}>THỬ TRỰC TIẾP</p><h2>Tiếp tục với bản nháp.</h2><p>Mở phần trò chuyện và biểu mẫu để thử bằng dữ liệu giả lập.</p><Link className={styles.primary} href="/demo/ct01" prefetch={false}>Thử trò chuyện với CT01 <ArrowRight size={16} aria-hidden="true" /></Link>
        </section>
      </aside>
    </div>
  </main>;
}
