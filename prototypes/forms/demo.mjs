import { FormSession } from './state.mjs';

const state = new FormSession([
  { id: 'demo_name', label: 'Demo name', required: true, maxLength: 80 },
  { id: 'demo_note', label: 'Demo note', maxLength: 500 },
]);
const samples = {
  'sample-a': { demo_name: 'Nguyễn Văn Mẫu', demo_note: 'Synthetic sample A. Edit this note to check export invalidation.' },
  'sample-b': { demo_name: 'Synthetic Example B', demo_note: 'Synthetic sample B. No values from sample A should appear.' },
};
const $ = (id) => document.getElementById(id);
const controls = new Map();
let downloadUrl = null;

for (const field of state.fields) {
  const wrap = document.createElement('div'); wrap.className = 'field';
  const label = document.createElement('label'); label.htmlFor = field.id; label.textContent = field.label;
  const input = document.createElement(field.id === 'demo_note' ? 'textarea' : 'input');
  input.id = field.id; input.autocomplete = 'off'; input.required = field.required;
  const error = document.createElement('p'); error.id = `${field.id}-error`; error.className = 'error';
  input.setAttribute('aria-describedby', error.id);
  input.addEventListener('input', () => { state.edit(field.id, input.value); render(); });
  wrap.append(label, input, error); $('fields').append(wrap); controls.set(field.id, { input, error });
}

function render() {
  const snapshot = state.snapshot();
  for (const [id, { input, error }] of controls) {
    const value = snapshot.values[id] ?? '';
    if (input.value !== value) input.value = value;
    input.disabled = snapshot.phase !== 'ready';
    error.textContent = snapshot.errors[id] ?? '';
    input.setAttribute('aria-invalid', String(Boolean(snapshot.errors[id])));
  }
  $('checked').checked = snapshot.checked;
  $('checked').disabled = !snapshot.valid || snapshot.exporting;
  $('prepare').disabled = !snapshot.valid || !snapshot.checked || snapshot.exporting;
  $('correction').disabled = snapshot.phase !== 'ready';
  $('revision').textContent = snapshot.phase === 'ready' ? `${snapshot.sessionId} · revision ${snapshot.revision}` : '';
  $('preview').textContent = snapshot.phase === 'ready' ? JSON.stringify(snapshot.values, null, 2) : 'No session data loaded.';
  $('status').textContent = snapshot.error ?? (snapshot.phase === 'loading' ? 'Loading sample…' : snapshot.phase === 'ready' ? snapshot.exporting ? 'Preparing current review copy…' : state.document() ? 'Review copy ready. Any edit will invalidate it.' : 'Changes stay in this tab. Check the preview before exporting.' : 'Session cleared. Select a demo session to continue.');
  if (downloadUrl) { URL.revokeObjectURL(downloadUrl); downloadUrl = null; }
  const artifact = state.document();
  $('download').hidden = !artifact;
  $('download').removeAttribute('href'); $('download').removeAttribute('download');
  if (artifact) {
    downloadUrl = URL.createObjectURL(artifact.blob);
    $('download').href = downloadUrl; $('download').download = artifact.filename;
  }
}

function loadSample() {
  const token = state.beginLoad($('session').value); render();
  // The real adapter must authorize access and supply resolved current answers.
  const values = samples[$('session').value];
  queueMicrotask(() => { state.finishLoad(token, values); render(); });
}

$('session').addEventListener('change', loadSample);
$('clear').addEventListener('click', () => { state.clear(); $('session').selectedIndex = -1; render(); });
$('correction').addEventListener('click', () => { state.replaceAnswers({ demo_name: 'Corrected synthetic example', demo_note: '' }); render(); });
$('checked').addEventListener('change', () => {
  if ($('checked').checked) state.confirmValues();
  else state.revokeConfirmation();
  render();
});
$('prepare').addEventListener('click', async () => {
  const { token, snapshot } = state.beginExport(); render();
  try {
    // Delayed mock adapter makes edit/session races visible; it does not produce an official PDF.
    await new Promise((resolve) => setTimeout(resolve, 300));
    const blob = new Blob([JSON.stringify({ kind: 'synthetic-review', sessionId: snapshot.sessionId, revision: snapshot.revision, templateVersion: snapshot.templateVersion, values: snapshot.values }, null, 2)], { type: 'application/json' });
    state.finishExport(token, { blob, filename: `synthetic-review-${snapshot.revision}.json` });
  } catch { state.failExport(token); }
  render();
});
window.addEventListener('pagehide', () => { state.clear(); $('session').selectedIndex = -1; render(); });
loadSample();
