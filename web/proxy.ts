import { clerkMiddleware } from '@clerk/nextjs/server';
import { NextResponse, type NextRequest, type NextFetchEvent } from 'next/server';
import { isLocalProvider, isPrivatePage, localOrigin, LOCAL_COOKIE } from './lib/local-auth-policy';
import { lookupLocalSession } from './lib/server/local-session';

const parties = (process.env.CLERK_AUTHORIZED_PARTIES ?? '').split(',').map((value) => value.trim()).filter(Boolean);
const enabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY && parties.length);
const clerk = enabled ? clerkMiddleware(() => NextResponse.next(), { authorizedParties: parties }) : null;
export default async function proxy(request: NextRequest, event: NextFetchEvent) {
  if (isLocalProvider()) {
    try {
      const origin = localOrigin();
      if (isPrivatePage(request.nextUrl.pathname)) {
        const session = await lookupLocalSession(request.cookies.get(LOCAL_COOKIE)?.value);
        if (session.status !== 'signed-in') {
          if (session.status === 'unconfigured') return new NextResponse('Authentication unavailable.', { status: 503, headers: { 'Cache-Control': 'no-store' } });
          const redirect = new URL('/login', origin);
          return NextResponse.redirect(redirect, { headers: { 'Cache-Control': 'no-store' } });
        }
      }
      const response = NextResponse.next();
      if (isPrivatePage(request.nextUrl.pathname) || request.nextUrl.pathname.startsWith('/api/')) response.headers.set('Cache-Control', 'no-store');
      return response;
    } catch { return new NextResponse('Authentication unavailable.', { status: 503, headers: { 'Cache-Control': 'no-store' } }); }
  }
  if (process.env.HOSO_AUTH_PROVIDER && process.env.HOSO_AUTH_PROVIDER !== 'clerk') return new NextResponse('Authentication unavailable.', { status: 503 });
  return clerk ? clerk(request, event) : NextResponse.next();
}
export const config = { matcher: ['/((?!_next|.*\\..*).*)', '/(api)(.*)', '/portal/:path*', '/workspace/:path*', '/chat/:path*', '/forms/:path*', '/research/:path*', '/documents/:path*', '/demo/:path*'] };
