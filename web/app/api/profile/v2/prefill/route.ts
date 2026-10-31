import { proxyProfileV2 } from '@/lib/server/profile-v2-proxy';
export const dynamic = 'force-dynamic';
export function POST(request: Request) { return proxyProfileV2(request, 'prefill'); }
