import { clerkMiddleware } from '@clerk/nextjs/server';
import { NextResponse, type NextRequest, type NextFetchEvent } from 'next/server';

const parties = (process.env.CLERK_AUTHORIZED_PARTIES ?? '').split(',').map((value) => value.trim()).filter(Boolean);
const enabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY && parties.length);
const clerk = enabled ? clerkMiddleware(() => NextResponse.next(), { authorizedParties: parties }) : null;
export default function proxy(request: NextRequest, event: NextFetchEvent) {
  return clerk ? clerk(request, event) : NextResponse.next();
}
export const config = { matcher: ['/((?!_next|.*\\..*).*)', '/(api)(.*)'] };
