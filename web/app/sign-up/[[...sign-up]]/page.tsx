import { SignUp } from '@clerk/nextjs';
import { clerkConfigured } from '@/lib/server/clerk';
export default function SignUpPage() {
  return <main className="auth-panel">{clerkConfigured() ? <SignUp /> : <section className="card"><h1>Account creation is not configured.</h1><p>Enable the managed Clerk connection before creating an account.</p></section>}</main>;
}
