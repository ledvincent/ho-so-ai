import Link from 'next/link';
import { redirect } from 'next/navigation';
import { Na5Catalog } from '@/components/na5-demo/catalog';
import { isLocalProvider } from '@/lib/local-auth-policy';
import { verifiedSession } from '@/lib/server/session';
export const dynamic = 'force-dynamic';
export default async function Research() {
  if (isLocalProvider()) {
    const session = await verifiedSession();
    if (session.status !== 'signed-in') redirect('/login');
  }
  return <><div style={{ maxWidth: 1100, margin: '20px auto 0', padding: '0 24px', fontSize: 12 }}><Link href="/workspace" prefetch={false}>← Trợ lý hồ sơ</Link></div><Na5Catalog workspaceHref="/workspace" /></>;
}