import { proxyChat } from '@/lib/server/chat-proxy';
export const dynamic = 'force-dynamic';
export function GET(request: Request) { return proxyChat(request, 'schema'); }
