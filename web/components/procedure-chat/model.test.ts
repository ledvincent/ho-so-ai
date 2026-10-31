import test from 'node:test';
import assert from 'node:assert/strict';
import { acceptsDiscoveryReply, currentCandidate, NA5_CODE, NA5_FORM, supportedWorkflow } from './model';
import { fixtureDiscovery, fixtureFormAdapter } from './fixtures';
import { emptyValues } from '@/components/na5-demo/model';

test('visa ambiguity and no-match fixtures never select a workflow', async () => {
  const signal = new AbortController().signal;
  const result = await fixtureDiscovery('ambiguous_visa').search('new visa', signal);
  assert.equal(result.candidates[0].code, '1.003342'); assert.equal(result.candidates.length, 2);
  const visa = await fixtureDiscovery('ambiguous_visa').detail(result.candidates[0], signal);
  assert.equal(supportedWorkflow(visa, NA5_FORM), false);
  assert.equal((await fixtureDiscovery('no_match').search('query', signal)).status, 'not_found');
  await assert.rejects(fixtureDiscovery('unavailable').search('query', signal));
});
test('opening NA5 requires the exact current procedure, chosen form and ready metadata', async () => {
  const adapter = fixtureDiscovery('stay_extension'); const signal = new AbortController().signal;
  const result = await adapter.search('test', signal); const detail = await adapter.detail(result.candidates[0], signal);
  assert.equal(supportedWorkflow(detail, null), false);
  assert.equal(supportedWorkflow(detail, 'b'.repeat(64)), false);
  assert.equal(supportedWorkflow({ ...detail, factsReady: false }, NA5_FORM), false);
  assert.equal(supportedWorkflow(detail, NA5_FORM), true);
  assert.equal(currentCandidate([], { code: NA5_CODE, name: 'prose' }), null);
});
test('aborted or superseded discovery responses are not accepted', () => {
  const controller = new AbortController();
  assert.equal(acceptsDiscoveryReply(1, 2, controller.signal), false);
  controller.abort(); assert.equal(acceptsDiscoveryReply(2, 2, controller.signal), false);
});
test('fixture form filling is deterministic and does not use any HTTP/provider transport', async () => {
  const original = globalThis.fetch; globalThis.fetch = async () => { throw new Error('No transport allowed'); };
  try {
    const result = await fixtureFormAdapter({ message: 'Fictional Viewer Test', values: emptyValues(), revision: 1, focusField: 'applicant_full_name', history: [], signal: new AbortController().signal });
    assert.equal(result.values.applicant_full_name, 'FICTIONAL VIEWER TEST');
  } finally { globalThis.fetch = original; }
});
