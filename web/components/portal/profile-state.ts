import { EMPTY_PROFILE, PROFILE_LIMITS, type ProfileFields, type ProfileRecord, type ProfileUpdate } from '../../lib/contracts';

export type ProfileProblem = 'signed-out' | 'conflict' | 'not-found' | 'not-implemented' | 'unavailable' | 'invalid' | 'rejected';
export type ProfileState = {
  fields: ProfileFields;
  revision: number | null;
  phase: 'idle' | 'loading' | 'ready' | 'saving' | 'blocked';
  dirty: boolean;
  saved: boolean;
  problem: ProfileProblem | null;
};
type FetchProfile = (url: string, init: RequestInit) => Promise<Response>;
const keys = Object.keys(EMPTY_PROFILE) as (keyof ProfileFields)[];
const blank = (): ProfileState => ({ fields: { ...EMPTY_PROFILE }, revision: null, phase: 'idle', dirty: false, saved: false, problem: null });

/** Treat upstream data as untrusted. This is a boundary check, not a rival schema. */
export function readProfile(value: unknown): ProfileRecord {
  if (typeof value !== 'object' || value === null) throw new TypeError('Invalid profile response');
  const record = value as Partial<ProfileRecord>;
  if (typeof record.profile_id !== 'string' || record.profile_id.length < 1 || record.profile_id.length > 256
    || !Number.isSafeInteger(record.revision) || record.revision! < 1
    || typeof record.fields !== 'object' || record.fields === null) throw new TypeError('Invalid profile response');
  const fields = { ...EMPTY_PROFILE };
  for (const key of keys) {
    const field = record.fields[key];
    if (field !== null && (typeof field !== 'string' || [...field].length > PROFILE_LIMITS[key])) throw new TypeError('Invalid profile response');
    fields[key] = field;
  }
  return { profile_id: record.profile_id, revision: record.revision!, fields };
}

export function problemForStatus(status: number): ProfileProblem {
  if (status === 401) return 'signed-out';
  if (status === 404) return 'not-found';
  if (status === 409) return 'conflict';
  if (status === 501) return 'not-implemented';
  if (status === 400 || status === 413 || status === 422) return 'invalid';
  if (status === 403) return 'rejected';
  return 'unavailable';
}

export const PROFILE_MESSAGES: Record<ProfileProblem, string> = {
  'signed-out': 'Phiên đăng nhập đã kết thúc. Vui lòng đăng nhập lại để mở hồ sơ.',
  conflict: 'Hồ sơ đã thay đổi ở nơi khác. Thay đổi của bạn chưa được lưu. Tải lại hồ sơ trước khi chỉnh sửa tiếp.',
  'not-found': 'Không tìm thấy hồ sơ hiện tại. Thay đổi của bạn chưa được lưu. Hãy tải lại hồ sơ.',
  'not-implemented': 'Chức năng lưu hồ sơ chưa được kết nối. Chưa có thay đổi nào được xác nhận lưu.',
  unavailable: 'Không thể kết nối hồ sơ lúc này. Chưa thể xác nhận thay đổi đã được lưu. Vui lòng thử lại.',
  invalid: 'Thông tin chưa hợp lệ hoặc quá dài. Kiểm tra các trường rồi thử lưu lại.',
  rejected: 'Yêu cầu bị từ chối. Chưa lưu thay đổi. Hãy tải lại trang từ địa chỉ ứng dụng.',
};

/** Client lifecycle only. Identity and ownership are always verified by the API. */
export class ProfileController {
  private state: ProfileState = blank();
  private baseline: ProfileFields = { ...EMPTY_PROFILE };
  private generation = 0;
  private pending: AbortController | null = null;
  private listeners = new Set<() => void>();

  constructor(private readonly request: FetchProfile = (url, init) => fetch(url, init)) {}

  snapshot = (): ProfileState => this.state;
  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => { this.listeners.delete(listener); };
  };
  private publish(state: ProfileState) {
    this.state = state;
    for (const listener of this.listeners) listener();
  }
  private invalidate() {
    this.generation += 1;
    this.pending?.abort();
    this.pending = null;
  }
  /** Called on unmount, account/session change and before sign-out. */
  reset() {
    this.invalidate();
    this.baseline = { ...EMPTY_PROFILE };
    this.publish(blank());
  }
  edit(field: keyof ProfileFields, value: string) {
    if (this.state.phase !== 'ready') return;
    const fields = { ...this.state.fields, [field]: value || null };
    this.publish({ ...this.state, fields, dirty: keys.some((key) => fields[key] !== this.baseline[key]), saved: false });
  }
  discard() {
    if (this.state.phase !== 'ready') return;
    this.publish({ ...this.state, fields: { ...this.baseline }, dirty: false, saved: false });
  }
  async load() {
    this.invalidate();
    this.baseline = { ...EMPTY_PROFILE };
    this.publish({ ...blank(), phase: 'loading' });
    await this.perform('GET');
  }
  async save() {
    if (this.state.phase !== 'ready' || this.state.revision === null || !this.state.dirty
      || this.state.problem === 'conflict' || this.state.problem === 'not-found') return;
    const payload: ProfileUpdate = { expected_revision: this.state.revision, fields: { ...this.state.fields } };
    this.invalidate();
    this.publish({ ...this.state, phase: 'saving', saved: false, problem: null });
    await this.perform('PUT', payload);
  }
  private async perform(method: 'GET' | 'PUT', payload?: ProfileUpdate) {
    const generation = this.generation;
    const pending = new AbortController();
    this.pending = pending;
    const timeout = setTimeout(() => pending.abort(), 12_000);
    try {
      const response = await this.request('/api/profile', {
        method, credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: pending.signal,
        headers: { Accept: 'application/json', ...(payload ? { 'Content-Type': 'application/json' } : {}) },
        ...(payload ? { body: JSON.stringify(payload) } : {}),
      });
      if (generation !== this.generation) return;
      if (response.status === 404 && method === 'GET') {
        this.publish({ ...blank(), phase: 'ready', revision: 0 });
        return;
      }
      if (!response.ok) {
        const problem = problemForStatus(response.status);
        if (problem === 'signed-out') {
          this.baseline = { ...EMPTY_PROFILE };
          this.publish({ ...blank(), phase: 'blocked', problem });
        } else {
          this.publish({ ...this.state, phase: method === 'GET' ? 'blocked' : 'ready', problem, saved: false });
        }
        return;
      }
      const record = readProfile(await response.json());
      if (generation !== this.generation) return;
      if (payload && record.revision <= payload.expected_revision) throw new TypeError('Stale profile response');
      this.baseline = { ...record.fields };
      this.publish({ fields: { ...record.fields }, revision: record.revision, phase: 'ready', dirty: false, saved: method === 'PUT', problem: null });
    } catch {
      if (generation !== this.generation) return;
      this.publish({ ...this.state, phase: method === 'GET' ? 'blocked' : 'ready', problem: 'unavailable', saved: false });
    } finally {
      clearTimeout(timeout);
      if (generation === this.generation) this.pending = null;
    }
  }
}
