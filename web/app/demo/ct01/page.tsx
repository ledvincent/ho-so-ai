import type { Metadata } from 'next';
import { Ct01Demo } from '@/components/ct01-demo/ct01-demo';

export const metadata: Metadata = { title: 'CT01 · Bản thử nghiệm | Hồ Sơ AI', description: 'Thử điền ba mục trên bản nền CT01; chỉ dùng dữ liệu giả.' };
export default function Ct01DemoPage() { return <Ct01Demo />; }
