import { redirect } from 'next/navigation';
import { isLocalProvider } from '@/lib/local-auth-policy';
import { verifiedSession } from '@/lib/server/session';
import { ConnectedLogin } from '@/components/guided-portal/login-connected';
export const dynamic = 'force-dynamic';
export default async function Login() {
  if (!isLocalProvider()) redirect('/sign-in');
  const session = await verifiedSession();
  if (session.status === 'signed-in') redirect('/workspace');
  return <ConnectedLogin />;
}
