export type AuthCase = 'loading' | 'signed-out' | 'a-1' | 'a-2' | 'b-1';
export type ResponseCase = 'valid' | 'malformed' | '404' | '401' | '503';
type PendingView = { id: number; auth: AuthCase; response: ResponseCase; aborted: boolean };
type HarnessState = {
  auth: AuthCase;
  response: ResponseCase;
  delayed: boolean;
  pending: PendingView[];
  events: string[];
};

// Ephemeral scenario controls only: no tokens, cookies, storage or profile repository.
let state: HarnessState = { auth: 'a-1', response: 'valid', delayed: false, pending: [], events: [] };
let requestNumber = 0;
const listeners = new Set<() => void>();
const replies = new Map<number, { resolve: (response: Response) => void; reply: () => Response; detach: () => void }>();

export const snapshot = () => state;
export const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener); }; };
function publish(patch: Partial<HarnessState>) {
  state = { ...state, ...patch };
  listeners.forEach(listener => listener());
}
export function record(message: string) { publish({ events: [...state.events, message].slice(-24) }); }
export function setAuth(auth: AuthCase) { publish({ auth }); record(`AUTH scenario → ${auth}`); }
export function setResponse(response: ResponseCase) { publish({ response }); }
export function setDelayed(delayed: boolean) { publish({ delayed }); }
export function clearEvents() { publish({ events: [] }); }

export function authValues(auth = state.auth) {
  const signedIn = auth === 'a-1' || auth === 'a-2' || auth === 'b-1';
  const account = auth === 'b-1' ? 'B' : 'A';
  return {
    isLoaded: auth !== 'loading',
    isSignedIn: signedIn,
    userId: signedIn ? `TEST-ONLY-user-${account}` : null,
    sessionId: signedIn ? `TEST-ONLY-${auth}` : null,
  };
}

function jsonResponse(body: unknown, status: number) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
}
function replyFor(response: ResponseCase, auth: AuthCase) {
  if (response === 'malformed') return jsonResponse({ profile_id: 'TEST-ONLY-malformed', revision: 1, fields: { full_name: 123 } }, 200);
  if (response !== 'valid') {
    const status = Number(response);
    const code = status === 404 ? 'PROFILE_NOT_FOUND' : status === 401 ? 'TEST_HARNESS_SIGNED_OUT' : 'PROFILE_UNAVAILABLE';
    return jsonResponse({ detail: { code } }, status);
  }
  const account = auth === 'b-1' ? 'B' : 'A';
  return jsonResponse({
    profile_id: `TEST-ONLY-profile-${account}`,
    revision: 1,
    fields: {
      full_name: `Người Mẫu ${account}`,
      date_of_birth: account === 'A' ? '1990-01-01' : '1992-02-02',
      nationality: `Quốc tịch giả lập ${account}`,
      address: `Địa chỉ giả lập ${account}\nKhông có địa chỉ thực`,
      phone_number: account === 'A' ? '+00 000000001' : '+00 000000002',
      email: `${account.toLowerCase()}@synthetic.invalid`,
    },
  }, 200);
}

export function resolveDelayed(id: number) {
  const pending = replies.get(id);
  if (!pending) return;
  replies.delete(id);
  pending.detach();
  publish({ pending: state.pending.filter(item => item.id !== id) });
  record(`#${id} forced delayed reply delivered (even after abort; test only)`);
  pending.resolve(pending.reply());
}

export function installMockFetch() {
  // Never delegate to native fetch. Only GET /api/profile receives fixture data;
  // every other endpoint returns 503 without contacting a service or proxy.
  globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : null;
    const url = new URL(request ? request.url : String(input), window.location.origin);
    const method = (init?.method ?? request?.method ?? 'GET').toUpperCase();
    const signal = init?.signal ?? request?.signal ?? null;
    if (url.origin !== window.location.origin || url.pathname !== '/api/profile' || url.search || method !== 'GET') {
      record(`BLOCKED ${method} ${url.pathname} → synthetic 503 (no network)`);
      return Promise.resolve(jsonResponse({ code: 'TEST_HARNESS_SERVICE_UNAVAILABLE' }, 503));
    }
    const id = ++requestNumber;
    const auth = state.auth;
    const response = state.response;
    const reply = () => replyFor(response, auth);
    record(`#${id} GET /api/profile · ${auth} · ${response}${state.delayed ? ' · held' : ' · immediate'}`);
    if (!state.delayed) {
      if (signal?.aborted) return Promise.reject(new DOMException('Synthetic request was aborted', 'AbortError'));
      return Promise.resolve(reply());
    }
    // Intentionally ignore cancellation for this controllable late-response test.
    // Actual component generation/revision guards must reject a stale response.
    return new Promise<Response>(resolve => {
      const onAbort = () => {
        publish({ pending: state.pending.map(item => item.id === id ? { ...item, aborted: true } : item) });
        record(`#${id} abort observed; reply remains held for stale-response test`);
      };
      replies.set(id, { resolve, reply, detach: () => signal?.removeEventListener('abort', onAbort) });
      signal?.addEventListener('abort', onAbort, { once: true });
      publish({ pending: [...state.pending, { id, auth, response, aborted: Boolean(signal?.aborted) }] });
    });
  };
}

export function emitPageEvent(type: 'pagehide' | 'pageshow') {
  record(`SYNTHETIC ${type} event · persisted=true (no real browser freeze)`);
  window.dispatchEvent(new PageTransitionEvent(type, { persisted: true }));
}
