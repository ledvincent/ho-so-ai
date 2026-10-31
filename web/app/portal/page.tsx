import Link from 'next/link';
import { verifiedSession } from '@/lib/server/clerk';
export const dynamic = 'force-dynamic';
export default async function Portal() {
  const session = await verifiedSession();
  if (session.status === 'unconfigured') return <main className="setup-panel"><p className="eyebrow">Account setup</p><h1>Your dossier starts here.</h1><p>Clerk is not configured in this environment. No account information is loaded.</p><Link className="button primary" href="/forms/demo">Try the synthetic form</Link></main>;
  if (session.status === 'signed-out') return <main className="setup-panel"><h1>Sign in to open your dossier.</h1><Link className="button primary" href="/sign-in">Sign in</Link></main>;
  return <main className="setup-panel"><p className="eyebrow">Authenticated account</p><h1>Your dossier</h1><p>Your session is verified. The portal workstream will connect the private profile, session list and document history here.</p><Link className="button primary" href="/forms/demo">Prepare a form</Link></main>;
}
