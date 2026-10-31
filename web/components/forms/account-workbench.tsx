'use client';
import { useAuth } from '@clerk/nextjs';
import { FormWorkbench } from './form-workbench';
export function AccountWorkbench() {
  const { userId, isLoaded } = useAuth();
  return <FormWorkbench key={userId ?? 'anonymous'} accountState={isLoaded && userId ? 'signed-in' : 'signed-out'} accountKey={userId ?? 'anonymous'} />;
}
