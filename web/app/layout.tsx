import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import Link from 'next/link';
import { clerkConfigured } from '@/lib/server/clerk';
import './globals.css';

export const metadata: Metadata = { title: 'Hồ Sơ AI', description: 'Prepare and review your administrative documents.' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const shell = <><header className="site-header"><Link className="brand" href="/"><span className="brand-mark">h.</span><span>Hồ Sơ <b>AI</b></span></Link><nav aria-label="Main navigation"><Link href="/forms/demo">Prepare a form</Link><Link href="/portal">My dossier</Link></nav><Link className="header-account" href="/sign-in">My account <span aria-hidden="true">↗</span></Link></header>{children}<footer className="site-footer"><span>Hồ Sơ AI</span><span>Review your information before using a document.</span></footer></>;
  return <html lang="en"><body>{clerkConfigured() ? <ClerkProvider>{shell}</ClerkProvider> : shell}</body></html>;
}
