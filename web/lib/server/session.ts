import 'server-only';
import { cookies } from 'next/headers';
import { verifiedSession as clerkSession } from './clerk';
import { lookupLocalSession } from './local-session';
import { isLocalProvider, LOCAL_COOKIE } from '../local-auth-policy';

export async function verifiedSession() {
  if (isLocalProvider()) return lookupLocalSession((await cookies()).get(LOCAL_COOKIE)?.value);
  if (process.env.HOSO_AUTH_PROVIDER && process.env.HOSO_AUTH_PROVIDER !== 'clerk') return { status: 'unconfigured' as const };
  return clerkSession();
}
