import { SignIn } from '@clerk/nextjs';
import { clerkConfigured } from '@/lib/server/clerk';
export default function SignInPage() {
  return <main className="auth-panel">{clerkConfigured() ? <SignIn /> : <section className="card"><h1>Account connection is not configured.</h1><p>The portal owner must configure Clerk keys and username/password sign-in. This page does not collect credentials.</p></section>}</main>;
}
