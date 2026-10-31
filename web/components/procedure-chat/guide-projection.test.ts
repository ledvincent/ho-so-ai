import test from 'node:test';
import assert from 'node:assert/strict';
import { candidateLabel, guideCopy, guideFor, guideText } from './guide-projection';
import type { ProcedureDetail } from './model';
import { createDiscoveryAdapter } from './api';
import type { LocalSession } from '@/components/guided-portal/api';
import { translate } from '@/components/ui/locale-text';

function detail(code: string): ProcedureDetail {
  const guide = guideCopy[code];
  return { candidate: { code, name: guide.title.vi }, forms: [], provenance: [], fixture: false, factsReady: false, sourceVersion: guide.source.sha256 };
}

test('all four guides bind to their own source and never fall back to another procedure or snapshot', () => {
  assert.deepEqual(Object.keys(guideCopy).sort(), ['1.000771', '1.001146', '1.003326', '1.003342']);
  for (const code of Object.keys(guideCopy)) {
    assert.equal(guideFor(detail(code))?.procedure_code, code);
    assert.equal(guideFor({ ...detail(code), sourceVersion: 'changed' }), null);
    assert.equal(guideFor({ ...detail(code), fixture: true }), null);
  }
});

test('visa-exemption guide remains useful without a form: three documents, separate online instruction, three steps', () => {
  const guide = guideFor(detail('1.000771'))!;
  const documents = guide.checklist.filter(item => item.kind === 'document');
  assert.equal(documents.length, 3);
  assert.ok(documents.some(item => /NA5/.test(item.title.en)));
  assert.ok(documents.some(item => /exemption/i.test(item.title.en)));
  assert.ok(documents.some(item => / or /i.test(item.text.en)));
  assert.ok(documents.every(item => item.originals === 1 && item.copies === 0));
  const instruction = guide.checklist.filter(item => item.kind === 'submission_instruction');
  assert.equal(instruction.length, 1);
  assert.equal(instruction[0].originals, 0);
  assert.match(instruction[0].text.en, /postal/i);
  assert.equal(guide.steps.length, 3);
});

test('bilingual projection preserves source quotations, conditions, alternatives and unknown counts', () => {
  for (const guide of Object.values(guideCopy)) {
    for (const row of [...guide.checklist, ...guide.steps]) {
      assert.ok(guideText(row.title, 'en').trim());
      assert.ok(guideText(row.text, 'en').trim());
      assert.ok(guideText(row.text, 'vi').trim());
      assert.ok(row.source_ref.quote_vi.trim());
    }
    assert.ok(guide.conditions.length > 0);
  }
  for (const code of ['1.001146', '1.003326', '1.003342']) {
    assert.ok(guideCopy[code].conditions.some(condition => /relationship|relative|family/i.test(condition.text.en)));
  }
});

test('English labels do not mutate the original Vietnamese identity used for selection', () => {
  const candidate = { ...detail('1.000771').candidate, nameEn: 'Catalog English title' };
  const original = { ...candidate };
  assert.equal(candidateLabel(candidate, 'en'), 'Catalog English title');
  assert.equal(candidateLabel(candidate, 'vi'), candidate.name);
  assert.deepEqual(candidate, original);
  assert.match(candidateLabel(detail('1.000771').candidate, 'en'), /exemption/i);
});

test('detail retains catalog English name and original source sections without replacing the original name', async () => {
  const identity: LocalSession = { user: { id: 'fictional-guide-user', username: 'fixture', identity_provider: 'local' }, expires_at: 1900000000 };
  const candidate = { code: '1.000771', name: 'Tên gốc', nameEn: 'English title' };
  const adapter = createDiscoveryAdapter(identity, (async path => path === '/api/auth/session' ? Response.json(identity) : Response.json({ code: candidate.code, name: candidate.name, forms: [], analysis: { facts_ready: false }, document_json: { sections: [{ heading: 'Trình tự', text_verbatim: 'Nguyên văn nguồn' }] } })) as typeof fetch);
  const result = await adapter.detail(candidate, new AbortController().signal);
  assert.equal(result.candidate.name, candidate.name);
  assert.equal(result.candidate.nameEn, candidate.nameEn);
  assert.deepEqual(result.sourceSections, [{ heading: 'Trình tự', text: 'Nguyên văn nguồn' }]);
});

test('English form prompts and primary actions are authored UI copy, with field identities unchanged', () => {
  assert.equal(translate('en', 'Điền biểu mẫu này'), 'Fill this form');
  assert.equal(translate('en', 'Đã cập nhật bản nháp.'), 'Draft updated.');
  assert.equal(translate('en', 'Mục tiếp theo: Current nationality. Bạn vui lòng bổ sung thông tin này.'), 'Next field: Current nationality. Please provide this information.');
  assert.equal(translate('vi', 'Mục tiếp theo: Current nationality. Bạn vui lòng bổ sung thông tin này.'), 'Mục tiếp theo: Quốc tịch hiện nay. Bạn vui lòng bổ sung thông tin này.');
});
