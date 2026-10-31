/** Runtime checks for the e162 public wire contract, not another form schema. */
import { DiscoveryError } from './errors';
import type { DiscoveryChatRequest, DiscoveryDocumentDownload, DiscoveryDocumentPages, DiscoveryDocumentSchema, DiscoveryDocumentValues, DiscoveryFormAction, JsonObject } from './document-types';

export const DOCUMENT_ID = /^[a-z0-9][a-z0-9_-]{0,99}$/;
const CODE = /^[0-9]\.[0-9]{6}$/;
const HASH = /^[a-f0-9]{64}$/;
const SAFE_FIELD = /^[A-Za-z0-9_][A-Za-z0-9_.:-]{0,127}$/;
const forbiddenKeys = new Set(['__proto__', 'prototype', 'constructor']);
function invalid(): never { throw new DiscoveryError(502, 'DISCOVERY_INVALID_RESPONSE'); }
function badRequest(): never { throw new DiscoveryError(422, 'INVALID_REQUEST'); }
function record(value: unknown): JsonObject { if (!value || typeof value !== 'object' || Array.isArray(value)) invalid(); return value as JsonObject; }
function list(value: unknown): unknown[] { if (!Array.isArray(value)) invalid(); return value; }
function text(value: unknown, max: number, empty = false): string {
  if (typeof value !== 'string' || (!empty && !value.trim()) || [...value].length > max) invalid();
  return value;
}
function bool(value: unknown): boolean { if (typeof value !== 'boolean') invalid(); return value; }
function hash(value: unknown): string { const result = text(value, 64); if (!HASH.test(result)) invalid(); return result; }
function procedure(value: unknown): string { const result = text(value, 8); if (!CODE.test(result)) invalid(); return result; }
function uniqueStrings(value: unknown, count = 2000, length = 16000): string[] {
  const items = list(value).map(item => text(item, length));
  if (items.length > count || new Set(items).size !== items.length) invalid();
  return items;
}
function knownKeys(value: JsonObject, keys: readonly string[]): void { if (Object.keys(value).some(key => !keys.includes(key))) invalid(); }
function url(value: unknown): string {
  const result = text(value, 8000);
  if (!/^https?:\/\//iu.test(result) || /[\u0000-\u0020\u007f\\]/u.test(result)) invalid();
  try {
    const parsed = new URL(result);
    if (!['https:', 'http:'].includes(parsed.protocol) || !parsed.hostname || parsed.username || parsed.password || /@/u.test(result.split('/').slice(0, 3).join('/'))) invalid();
  } catch { invalid(); }
  return result;
}
export function documentId(value: string): string { if (!DOCUMENT_ID.test(value)) badRequest(); return value; }

const actionSuffixes = {
  schema_url: 'schema', template_url: 'template', template_pages_url: 'template-pages', validate_url: 'validate',
  preview_url: 'preview', preview_pages_url: 'preview-pages', download_url: 'download',
} as const;
export function formAction(value: unknown, expectedProcedure?: string): DiscoveryFormAction {
  const input = record(value);
  const document_id = text(input.document_id, 100);
  if (!DOCUMENT_ID.test(document_id)) invalid();
  const procedure_code = procedure(input.procedure_code);
  if (expectedProcedure && procedure_code !== expectedProcedure) invalid();
  const result: JsonObject = {
    document_id, procedure_code, form_id: text(input.form_id, 100),
    template_sha256: hash(input.template_sha256), template_version: hash(input.template_version),
    revision: text(input.revision, 500), review_status: text(input.review_status, 100),
    applicability: text(input.applicability ?? 'unresolved', 200), download_available: bool(input.download_available),
  };
  if (result.download_available && result.review_status !== 'reviewed') invalid();
  for (const [key, suffix] of Object.entries(actionSuffixes)) {
    if (input[key] !== `/documents/${document_id}/${suffix}`) invalid();
    result[key] = `/api/discovery/documents/${document_id}/${suffix}`;
  }
  return result as DiscoveryFormAction;
}
export function documentSchema(value: unknown, expectedId: string): DiscoveryDocumentSchema {
  const input = record(value);
  if (input.document_id !== expectedId) invalid();
  const result: JsonObject = {
    document_id: expectedId, procedure_code: procedure(input.procedure_code), form_id: text(input.form_id, 100),
    name: text(input.name, 2000), revision: text(input.revision, 500), effective_from: input.effective_from === null ? null : text(input.effective_from, 100),
    review_status: text(input.review_status, 100), applicability: text(input.applicability, 200),
    download_available: bool(input.download_available), template_sha256: hash(input.template_sha256), template_version: hash(input.template_version),
  };
  if (result.download_available && result.review_status !== 'reviewed') invalid();
  if (!Number.isSafeInteger(input.page_count) || (input.page_count as number) < 1 || (input.page_count as number) > 100) invalid();
  result.page_count = input.page_count;
  const fields = list(input.fields).map(record);
  if (!fields.length || fields.length > 2000) invalid();
  const ids = new Set<string>();
  for (const field of fields) {
    const key = text(field.id, 128);
    if (!SAFE_FIELD.test(key) || forbiddenKeys.has(key) || ids.has(key)) invalid();
    ids.add(key); text(field.label, 2000); text(field.type, 64);
    for (const flag of ['required', 'manual', 'inactive', 'hidden', 'uppercase', 'multiline', 'repeat']) if (flag in field) bool(field[flag]);
    if (field.max_length != null && (!Number.isSafeInteger(field.max_length) || (field.max_length as number) < 1 || (field.max_length as number) > 16000)) invalid();
    if (field.options != null) uniqueStrings(field.options, 200, 1000);
  }
  for (const field of fields) {
    if (field.when != null) for (const [key, condition] of Object.entries(record(field.when))) { if (!ids.has(key)) invalid(); text(condition, 16000, true); }
  }
  const fixed = record(input.fixed_values);
  for (const [key, fixedValue] of Object.entries(fixed)) { if (!ids.has(key)) invalid(); text(fixedValue, 16000, true); }
  const dateOrder = list(input.date_order).map(pair => {
    const names = uniqueStrings(pair, 2, 128);
    if (names.length !== 2 || names.some(name => !ids.has(name))) invalid();
    return names;
  });
  result.fields = fields; result.fixed_values = fixed; result.date_order = dateOrder;
  return result as DiscoveryDocumentSchema;
}
function valueMap(value: unknown, fail: () => never, allowed?: Set<string>): Record<string, string> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail();
  const entries = Object.entries(value as JsonObject);
  if (entries.length > 2000) fail();
  for (const [key, item] of entries) if (!SAFE_FIELD.test(key) || forbiddenKeys.has(key) || (allowed && !allowed.has(key)) || typeof item !== 'string' || [...item].length > 16000) fail();
  return value as Record<string, string>;
}
export function documentValues(value: unknown, schema: DiscoveryDocumentSchema, download = false): DiscoveryDocumentValues | DiscoveryDocumentDownload {
  if (!value || typeof value !== 'object' || Array.isArray(value)) badRequest();
  const input = value as JsonObject;
  if (Object.keys(input).some(key => !['values', 'template_version', ...(download ? ['review_token', 'confirmed'] : [])].includes(key))) badRequest();
  if (typeof input.template_version !== 'string' || !HASH.test(input.template_version)) badRequest();
  if (input.template_version !== schema.template_version) throw new DiscoveryError(409, 'WORKFLOW_VERSION_MISMATCH');
  const values = valueMap(input.values, badRequest, new Set(schema.fields.map(field => field.id as string)));
  const result = { values, template_version: input.template_version };
  if (download) {
    if (input.confirmed !== true || typeof input.review_token !== 'string' || !input.review_token || input.review_token.length > 131072 || /[\u0000-\u0020\u007f]/u.test(input.review_token)) badRequest();
    return { ...result, review_token: input.review_token, confirmed: true };
  }
  return result;
}
export function validationResult(value: unknown, schema: DiscoveryDocumentSchema): JsonObject {
  const input = record(value);
  if (input.template_version !== schema.template_version) throw new DiscoveryError(409, 'WORKFLOW_VERSION_MISMATCH');
  const fields = new Map(schema.fields.map(field => [field.id as string, field]));
  const values = valueMap(input.values, invalid, new Set(fields.keys()));
  const seen = new Set<string>();
  const missing = list(input.missing_fields).map(value => {
    const item = record(value), key = text(item.id, 128);
    if (!fields.has(key) || seen.has(key) || item.label !== fields.get(key)?.label) invalid();
    seen.add(key); return { id: key, label: item.label };
  });
  if (missing.length > fields.size || bool(input.ready_for_preview) !== (missing.length === 0)) invalid();
  return { values, missing_fields: missing, ready_for_preview: input.ready_for_preview, template_version: input.template_version, note: text(input.note, 4000) };
}
export function pagesResult(value: unknown, schema: DiscoveryDocumentSchema): DiscoveryDocumentPages {
  const input = record(value);
  if (input.template_version !== schema.template_version) throw new DiscoveryError(409, 'WORKFLOW_VERSION_MISMATCH');
  const pages = list(input.pages);
  if (pages.length !== schema.page_count) invalid();
  return { template_version: schema.template_version, pages: pages.map((value, index) => {
    const page = record(value);
    if (page.page_number !== index + 1) invalid();
    const data = page.image_data_url;
    // This is an ASCII data URL, not prose: avoid expanding megabytes into a
    // code-point array and avoid repeated-group regex backtracking on image data.
    if (typeof data !== 'string' || data.length > 12 * 1024 * 1024) invalid();
    const prefix = 'data:image/png;base64,';
    if (!data.startsWith(prefix)) invalid();
    const encoded = data.slice(prefix.length);
    if (encoded.length % 4 !== 0 || !/^[A-Za-z0-9+/]*={0,2}$/u.test(encoded)) invalid();
    const bytes = Buffer.from(encoded, 'base64');
    if (bytes.length > 10 * 1024 * 1024 || !bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) invalid();
    return { page_number: index + 1, image_data_url: data };
  }) };
}
export function reviewToken(response: Response): string {
  const token = response.headers.get('x-review-token');
  if (!token || token.length > 131072 || /[\u0000-\u0020\u007f]/u.test(token)) invalid();
  return token;
}
export function chatRequest(value: unknown): DiscoveryChatRequest {
  if (!value || typeof value !== 'object' || Array.isArray(value)) badRequest();
  const input = value as JsonObject;
  if (Object.keys(input).some(key => !['message', 'procedure_code', 'history', 'retrieval_state', 'clarification_answer'].includes(key))) badRequest();
  if (typeof input.message !== 'string' || [...input.message.trim()].length < 2 || [...input.message.trim()].length > 1000) badRequest();
  if (input.procedure_code != null && (typeof input.procedure_code !== 'string' || !CODE.test(input.procedure_code))) badRequest();
  const history = input.history === undefined ? [] : input.history;
  if (!Array.isArray(history) || history.length > 12) badRequest();
  const turns = history.map(value => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) badRequest();
    const turn = value as JsonObject;
    if (Object.keys(turn).some(key => !['role', 'content'].includes(key)) || !['user', 'assistant'].includes(turn.role as string) || typeof turn.content !== 'string' || !turn.content.trim() || [...turn.content.trim()].length > 16000) badRequest();
    return { role: turn.role as 'user' | 'assistant', content: turn.content.trim() };
  });
  for (const [key, max] of [['retrieval_state', 12000], ['clarification_answer', 1000]] as const) {
    const item = input[key];
    if (item != null && (typeof item !== 'string' || !item || [...item].length > max || /[\u0000-\u001f\u007f]/u.test(item))) badRequest();
  }
  if (input.clarification_answer != null && (input.retrieval_state == null || input.procedure_code != null)) badRequest();
  return { message: input.message.trim(), history: turns,
    ...(input.procedure_code === undefined ? {} : { procedure_code: input.procedure_code as string | null }),
    ...(input.retrieval_state === undefined ? {} : { retrieval_state: input.retrieval_state as string | null }),
    ...(input.clarification_answer === undefined ? {} : { clarification_answer: input.clarification_answer as string | null }),
  };
}
function cards(value: unknown, refs: Set<string>, selectedCode?: string): JsonObject[] {
  const documents = list(value);
  if (documents.length > 200) invalid();
  const ids = new Set<string>();
  return documents.map(value => {
    const card = record(value), key = text(card.id, 128);
    if (ids.has(key) || !['fillable_form', 'supporting_document', 'submission_instruction'].includes(card.kind as string) || !['required', 'conditional', 'unconfirmed'].includes(card.requirement as string)) invalid();
    ids.add(key);
    const sourceIds = uniqueStrings(card.source_ids, 20, 64);
    if (sourceIds.some(item => !refs.has(item))) invalid();
    for (const count of ['originals', 'copies']) if (card[count] != null && (!Number.isSafeInteger(card[count]) || (card[count] as number) < 0)) invalid();
    return { id: key, title: text(card.title, 2000), kind: card.kind, requirement: card.requirement,
      condition: card.condition == null ? null : text(card.condition, 16000), description: text(card.description, 16000, true),
      originals: card.originals ?? null, copies: card.copies ?? null, source_ids: sourceIds,
      evidence_status: text(card.evidence_status, 100), form: card.form == null ? null : formAction(card.form, selectedCode) };
  });
}
export function chatResponse(value: unknown): JsonObject {
  const input = record(value);
  knownKeys(input, ['status', 'answer', 'citations', 'model', 'choices', 'retrieval_state', 'procedure_code', 'documents']);
  if (!['answered', 'insufficient_context', 'needs_clarification', 'out_of_scope'].includes(input.status as string)) invalid();
  const answer = text(input.answer, 16000);
  const citations = list(input.citations), ids = new Set<string>();
  if (citations.length > 20 || (input.status === 'answered' && !citations.length) || (input.status === 'out_of_scope' && citations.length)) invalid();
  const checked = citations.map(value => {
    const ref = record(value), key = text(ref.id, 64);
    knownKeys(ref, ['id', 'title', 'url']);
    if (!/^[A-Za-z0-9_-]+$/u.test(key) || ids.has(key)) invalid();
    ids.add(key); return { id: key, title: text(ref.title, 500), url: url(ref.url) };
  });
  // Document cards may add citations not printed inline. Every marker still resolves.
  for (const marker of answer.matchAll(/\[([^\[\]\n]+)\]/gu)) if (!ids.has(marker[1])) invalid();
  const choices = list(input.choices), choiceIds = new Set<string>();
  if (choices.length > 20) invalid();
  const checkedChoices = choices.map(value => {
    const choice = record(value), key = text(choice.id, 1000);
    knownKeys(choice, ['id', 'label']);
    if (choiceIds.has(key) || /[\u0000-\u001f\u007f]/u.test(key)) invalid();
    choiceIds.add(key); return { id: key, label: text(choice.label, 4000) };
  });
  const state = input.retrieval_state == null ? null : text(input.retrieval_state, 12000);
  if (state && /[\u0000-\u001f\u007f]/u.test(state)) invalid();
  if (choices.length && !state) invalid();
  const selected = input.procedure_code == null ? null : procedure(input.procedure_code);
  return { status: input.status, answer, citations: checked, model: input.model == null ? null : text(input.model, 256),
    choices: checkedChoices, retrieval_state: state, procedure_code: selected, documents: cards(input.documents, ids, selected ?? undefined) };
}
