import { proxyProfileV2 } from '@/lib/server/profile-v2-proxy';
export const dynamic = 'force-dynamic';
export function GET(request: Request) { return proxyProfileV2(request, 'read'); }
export function PUT(request: Request) { return proxyProfileV2(request, 'write'); }
