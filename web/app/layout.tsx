import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import { clerkConfigured } from '@/lib/server/clerk';
import { SiteShell } from '@/components/ui/site-shell';
import './globals.css';

export const metadata: Metadata = { title: 'Hồ Sơ AI', description: 'Chuẩn bị hồ sơ. Rà soát thông tin. Rõ ràng từng bước.' };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  const shell = <SiteShell>{children}</SiteShell>;
  return <html lang="vi"><body>{clerkConfigured() ? <ClerkProvider>{shell}</ClerkProvider> : shell}</body></html>;
}
