import { DemoSessionProvider } from '@/components/ct01-demo/demo-session';
export default function DemoLayout({ children }: { children: React.ReactNode }) {
  return <DemoSessionProvider>{children}</DemoSessionProvider>;
}
