import { proxyChat } from '@/lib/server/chat-proxy';
export const dynamic = 'force-dynamic';
export function POST(request: Request) { return proxyChat(request, 'assist'); }
