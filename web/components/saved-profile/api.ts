import { sameSession, sessionRequest, SessionExpired, type LocalSession } from '@/components/guided-portal/api';
import { EMPTY_PROFILE_DETAILS, PROFILE_V2_LIMITS, type ProfileV2Response, type ProfileV2Update, type PrefillRequest, type PrefillResponse } from '@/lib/profile-v2.generated';
import { flattenDetails, groupedDetails, sourceLabel } from './fields';
import type { PrefillClient } from './prefill-model';

export class ProfileError extends Error {
  constructor(public readonly status: number) { super('Profile request unavailable'); this.name = 'ProfileError'; }
}
const invalid = () => new ProfileError(503);
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw invalid();
  return value as Record<string, unknown>;
}
export function readProfileV2(raw: unknown): ProfileV2Response {
  const data = object(raw); const details = object(data.details); const legacy = object(data.legacy);
  if (data.schema_version !== 'profile.v2' || typeof data.profile_id !== 'string' || !data.profile_id || data.profile_id.length > 256 || !Number.isSafeInteger(data.revision) || Number(data.revision) < 1) throw invalid();
  const flat: Record<string, string | null> = {};
  for (const [group, fields] of Object.entries(EMPTY_PROFILE_DETAILS)) {
    const values = object(details[group]);
    for (const key of Object.keys(fields)) {
      const value = values[key] ?? null; const path = `${group}.${key}`;
      if (value !== null && (typeof value !== 'string' || [...value].length > (PROFILE_V2_LIMITS[path as keyof typeof PROFILE_V2_LIMITS] ?? 11))) throw invalid();
      if (path === 'basics.sex_as_on_document' && value !== null && !['M', 'F', 'X', 'unspecified'].includes(value as string)) throw invalid();
      flat[path] = value as string | null;
    }
  }
  for (const [key, limit] of [['nationality', 80], ['address', 300]] as const) if (legacy[key] != null && (typeof legacy[key] !== 'string' || [...(legacy[key] as string)].length > limit)) throw invalid();
  return { schema_version: 'profile.v2', profile_id: data.profile_id, revision: Number(data.revision), details: groupedDetails(flat), legacy: { nationality: (legacy.nationality as string | null) ?? null, address: (legacy.address as string | null) ?? null } };
}
const reasons: Record<string, string> = {
  unsupported_sex: 'Cần chọn câu trả lời phù hợp với biểu mẫu.',
  no_matching_applicant_field: 'Không có mục người đề nghị tương ứng trên tài liệu này.',
  legacy_meaning_ambiguous: 'Thông tin cũ chưa phân biệt ý nghĩa; hãy bổ sung trực tiếp khi được hỏi.',
  target_value_too_long: 'Thông tin dài hơn giới hạn của biểu mẫu; chưa sao chép.',
  target_multiline_not_supported: 'Thông tin nhiều dòng chưa phù hợp với mục của biểu mẫu.',
  target_validation_failed: 'Thông tin cần kiểm tra lại trước khi dùng trong tài liệu.',
  target_not_editable: 'Mục tương ứng không được điền trong quy trình này.',
};

/** Own-session seam only. Creating this client performs no profile read. */
export function createProfileClient(identity: LocalSession, fetcher: typeof fetch = fetch) {
  async function request(path: string, signal: AbortSignal, body?: unknown, method = body ? 'POST' : 'GET') {
    if (!sameSession(identity, await sessionRequest(signal, fetcher))) throw new SessionExpired();
    const response = await fetcher(path, { method, credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal, headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) });
    if (response.status === 401) throw new SessionExpired();
    if (!sameSession(identity, await sessionRequest(signal, fetcher))) throw new SessionExpired();
    if (!response.ok) throw new ProfileError(response.status);
    return response.json();
  }
  async function get(signal: AbortSignal) { return readProfileV2(await request('/api/profile/v2', signal)); }
  const prefill: PrefillClient = {
    async load(context, draft, signal) {
      const record = await get(signal);
      const body: PrefillRequest = { consent: true, applicant_confirmed: true, expected_revision: record.revision, request_id: crypto.randomUUID(), draft_revision: context.draftRevision, procedure_code: context.procedureCode, form_sha256: context.formSha, schema_version: context.schemaVersion, values: { ...draft } };
      const raw = object(await request('/api/profile/v2/prefill', signal, body));
      for (const key of ['request_id', 'draft_revision', 'procedure_code', 'form_sha256', 'schema_version'] as const) if (raw[key] !== body[key]) throw invalid();
      if (raw.profile_id !== record.profile_id || raw.profile_revision !== record.revision || raw.review_status !== 'draft' || !Array.isArray(raw.proposals) || raw.proposals.length > 30 || !Array.isArray(raw.unmapped) || raw.unmapped.length > 30) throw invalid();
      const sources: Record<string, string | null> = { ...flattenDetails(record.details), 'legacy.nationality': record.legacy.nationality ?? null, 'legacy.address': record.legacy.address ?? null };
      const rows = (raw.proposals as PrefillResponse['proposals']).map(proposal => {
        if (typeof proposal?.proposal_id !== 'string' || !proposal.proposal_id || typeof proposal.target_field !== 'string' || typeof proposal.value !== 'string' || !Array.isArray(proposal.source_fields) || !proposal.source_fields.length || proposal.source_fields.length > 2 || !proposal.source_values || !['direct', 'uppercase', 'document_sex', 'phone_only', 'email_only', 'phone_email'].includes(proposal.mapping)) throw invalid();
        for (const path of proposal.source_fields) if (!(path in sources) || typeof sources[path] !== 'string' || proposal.source_values[path] !== sources[path]) throw invalid();
        const existing = draft[proposal.target_field] ?? null;
        if (proposal.existing_value !== existing || proposal.requires_overwrite !== (existing !== null && existing !== '' && existing !== proposal.value)) throw invalid();
        return { id: proposal.proposal_id, target: proposal.target_field, value: proposal.value, sourceLabel: proposal.source_fields.map(sourceLabel).join(' + '), sourceValue: proposal.source_fields.map(path => proposal.source_values[path]).join(' / '), requiresDocument: proposal.source_fields.some(path => path.startsWith('passport.')) };
      });
      const warnings = (raw.unmapped as PrefillResponse['unmapped']).map(item => {
        if (!item || !(item.source_field in sources) || !reasons[item.reason]) throw invalid();
        return `${sourceLabel(item.source_field)}: ${reasons[item.reason]}`;
      });
      return { profileId: record.profile_id, revision: record.revision, rows, warnings };
    },
    async check(signal) { const record = await get(signal); return { profileId: record.profile_id, profileRevision: record.revision }; },
  };
  return {
    get,
    async save(update: ProfileV2Update, signal: AbortSignal) {
      const result = readProfileV2(await request('/api/profile/v2', signal, update, 'PUT'));
      if (result.revision <= update.expected_revision) throw invalid();
      return result;
    },
    prefill,
  };
}
export type ProfileClient = ReturnType<typeof createProfileClient>;
