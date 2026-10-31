import 'server-only';
import { auth } from '@clerk/nextjs/server';

export function clerkConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY && authorizedParties().length);
}
export function authorizedParties(): string[] {
  return (process.env.CLERK_AUTHORIZED_PARTIES ?? '').split(',').map((value) => value.trim()).filter(Boolean);
}
export async function verifiedSession() {
  if (!clerkConfigured() || authorizedParties().length === 0) return { status: 'unconfigured' as const };
  const session = await auth();
  if (!session.userId) return { status: 'signed-out' as const };
  const token = await session.getToken();
  if (!token) return { status: 'signed-out' as const };
  return { status: 'signed-in' as const, subject: session.userId, token };
}
