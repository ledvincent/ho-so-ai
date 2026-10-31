import { useSyncExternalStore } from 'react';
import { authValues, setAuth, snapshot, subscribe } from './state';

// Bundler alias used only by the explicit loopback harness, never by Next routes.
export function useAuth() {
  const current = useSyncExternalStore(subscribe, snapshot, snapshot);
  return { ...authValues(current.auth), signOut: async () => { setAuth('signed-out'); } };
}
