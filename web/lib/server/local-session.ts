import 'server-only';
import { apiUrl } from './api';
import { identityFrom, localOrigin, validSessionToken } from '../local-auth-policy';

export async function lookupLocalSession(token: string | undefined) {
  if (!validSessionToken(token)) return { status: 'signed-out' as const };
  try {
    localOrigin();
    const response = await fetch(apiUrl('/v1/auth/session'), { headers: { Authorization: `Bearer ${token}` }, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(5000) });
    if (response.status === 401) return { status: 'signed-out' as const };
    if (!response.ok) return { status: 'unconfigured' as const };
    const identity = identityFrom(await response.json());
    if (!identity) return { status: 'unconfigured' as const };
    return { status: 'signed-in' as const, subject: identity.user.id, token, ...identity };
  } catch { return { status: 'unconfigured' as const }; }
}
