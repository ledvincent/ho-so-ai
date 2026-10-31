import { proxyDemoForm } from '@/lib/server/form-proxy';
export const dynamic = 'force-dynamic';
export function POST(request: Request) { return proxyDemoForm(request, 'pdf'); }
