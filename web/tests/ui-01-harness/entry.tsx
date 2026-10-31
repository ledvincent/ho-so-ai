import { useSyncExternalStore } from 'react';
import { createRoot } from 'react-dom/client';
import { AccountWorkbench } from '@/components/forms/account-workbench';
import { clearEvents, emitPageEvent, installMockFetch, resolveDelayed, setAuth, setDelayed, setResponse, snapshot, subscribe, type AuthCase, type ResponseCase } from './state';
import './harness.css';

installMockFetch();

function Harness() {
  const state = useSyncExternalStore(subscribe, snapshot, snapshot);
  return <>
    <div className="harness-ribbon">TEST HARNESS / SYNTHETIC DATA ONLY / LOOPBACK — NO REAL AUTH OR BACKEND</div>
    <header className="harness-controls">
      <div className="harness-title"><h1>UI-01 isolated browser harness</h1><p>Actual AccountWorkbench → actual FormWorkbench. Test-only Clerk and Link shims. Every fetch stays in this tab; no profile is persisted.</p></div>
      <div className="harness-selectors">
        <label>Test auth scenario<select value={state.auth} onChange={event => setAuth(event.target.value as AuthCase)}>
          <option value="loading">Auth loading</option><option value="signed-out">Signed out</option><option value="a-1">Synthetic A / session 1</option><option value="a-2">Synthetic A / session 2</option><option value="b-1">Synthetic B / session 1</option>
        </select></label>
        <label>Next GET /api/profile response<select value={state.response} onChange={event => setResponse(event.target.value as ResponseCase)}>
          <option value="valid">200 — valid six-field synthetic profile</option><option value="malformed">200 — malformed profile</option><option value="404">404 — no saved profile</option><option value="401">401 — session expired</option><option value="503">503 — unavailable</option>
        </select></label>
      </div>
      <label className="harness-checkbox"><input type="checkbox" checked={state.delayed} onChange={event => setDelayed(event.target.checked)} />Hold profile responses until manually released (ignores abort, for stale-response testing)</label>
      <div className="harness-events"><button type="button" onClick={() => emitPageEvent('pagehide')}>Emit synthetic pagehide · persisted</button><button type="button" onClick={() => emitPageEvent('pageshow')}>Emit synthetic pageshow · persisted</button><button type="button" onClick={() => window.location.reload()}>Reload harness / reset all test state</button></div>
      {state.pending.length > 0 && <section className="harness-pending" aria-label="Held synthetic responses"><h2>Held responses</h2>{state.pending.map(item => <div key={item.id}><span>#{item.id} · {item.auth} · {item.response} · {item.aborted ? 'ABORT OBSERVED — force late reply' : 'waiting'}</span><button type="button" onClick={() => resolveDelayed(item.id)}>Resolve delayed request #{item.id}</button></div>)}</section>}
      <details className="harness-log"><summary>Test event log ({state.events.length})</summary><ol>{state.events.map((event, index) => <li key={`${index}-${event}`}>{event}</li>)}</ol><button type="button" onClick={clearEvents}>Clear event log</button></details>
      <p className="harness-expectations">Checks: A1 → A2 and A → B reset the draft; malformed 200 keeps it; 401 clears it; a held response released after a new session or edit must be ignored. PDF/preview requests always return a synthetic 503.</p>
    </header>
    <div className="harness-product" aria-label="Actual application components under test"><AccountWorkbench /></div>
  </>;
}

const root = document.getElementById('harness-root');
if (!root) throw new Error('Test harness root is missing');
createRoot(root).render(<Harness />);
