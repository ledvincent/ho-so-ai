'use client';
import { useRouter } from 'next/navigation';
import { loginRequest } from './api';
import { PortalLogin } from './login';

export function ConnectedLogin() {
  const router = useRouter();
  return <PortalLogin authenticate={async (username, password, signal) => { await loginRequest(username, password, signal); router.replace('/workspace'); router.refresh(); }} />;
}
