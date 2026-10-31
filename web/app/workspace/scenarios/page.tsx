import { redirect } from 'next/navigation';
import { verifiedSession } from '@/lib/server/session';
import { identityFrom, isLocalProvider } from '@/lib/local-auth-policy';
import { AuthenticatedPortal } from '@/components/guided-portal/authenticated';
export const dynamic = 'force-dynamic';
export default async function Scenarios() {
  if (!isLocalProvider()) redirect('/sign-in');
  const session = await verifiedSession(); const identity = identityFrom(session);
  if (session.status !== 'signed-in' || !identity) redirect('/login');
  return <AuthenticatedPortal session={identity} fixtures />;
}
