import type { ProfileV2Response } from '@/lib/profile-v2.generated';
import { ProfileError, type ProfileClient } from './api';
import { emptyDetails, flattenDetails, groupedDetails, profileFields } from './fields';

type State = { values: Record<string, string | null>; legacy: ProfileV2Response['legacy']; profileId: string | null; revision: number | null; phase: 'idle' | 'loading' | 'ready' | 'saving' | 'blocked'; dirty: boolean; saved: boolean; problem: number | null };
const blank = (): State => ({ values: flattenDetails(emptyDetails()), legacy: {}, profileId: null, revision: null, phase: 'idle', dirty: false, saved: false, problem: null });
export const profileProblem = (status: number) => status === 409 ? 'Hồ sơ đã thay đổi ở nơi khác. Các sửa đổi chưa được lưu. Tải lại hồ sơ trước khi lưu tiếp.' : status === 404 ? 'Không tìm thấy phiên bản hồ sơ hiện tại. Tải lại trước khi lưu.' : status === 422 ? 'Kiểm tra thông tin, giới hạn độ dài và ngày cấp / hết hạn trước khi lưu.' : 'Chưa thể xác nhận lưu hồ sơ. Các sửa đổi của bạn được giữ lại; hãy thử lại.';

/** Isolated editor draft; form edits never call this controller. */
export class RichProfileController {
  private state: State = blank();
  private baseline = this.state.values;
  private generation = 0;
  private pending: AbortController | null = null;
  private listeners = new Set<() => void>();
  constructor(private client: Pick<ProfileClient, 'get' | 'save'>, private saved: () => void = () => {}) {}
  snapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private publish(state: State) { this.state = state; this.listeners.forEach(listener => listener()); }
  private invalidate() { this.generation++; this.pending?.abort(); this.pending = null; }
  reset() { this.invalidate(); this.state = blank(); this.baseline = this.state.values; this.publish(this.state); }
  edit(id: string, value: string) {
    if (this.state.phase !== 'ready' || !profileFields.some(field => field.id === id)) return;
    const values = { ...this.state.values, [id]: value || null };
    this.publish({ ...this.state, values, dirty: JSON.stringify(values) !== JSON.stringify(this.baseline), saved: false });
  }
  cancel() { if (this.state.phase === 'ready') this.publish({ ...this.state, values: { ...this.baseline }, dirty: false, saved: false }); }
  load = () => this.run(false);
  save = () => {
    if (this.state.phase !== 'ready' || !this.state.dirty || this.state.revision === null || [404, 409].includes(this.state.problem ?? 0)) return Promise.resolve();
    return this.run(true);
  };
  private async run(save: boolean) {
    this.invalidate(); const attempt = this.generation; const pending = new AbortController(); this.pending = pending;
    const before = this.state; const expected = before.revision ?? 0;
    if (!save) { this.baseline = blank().values; this.publish({ ...blank(), phase: 'loading' }); }
    else this.publish({ ...before, phase: 'saving', saved: false, problem: null });
    const timer = setTimeout(() => pending.abort(), 12000);
    try {
      const record = save ? await this.client.save({ expected_revision: expected, details: groupedDetails(before.values) }, pending.signal) : await this.client.get(pending.signal);
      if (attempt !== this.generation || pending.signal.aborted) return;
      if (save && (record.revision <= expected || (before.profileId && record.profile_id !== before.profileId))) throw new ProfileError(503);
      const values = flattenDetails(record.details); this.baseline = values;
      this.publish({ values: { ...values }, legacy: record.legacy, profileId: record.profile_id, revision: record.revision, phase: 'ready', dirty: false, saved: save, problem: null });
      if (save) this.saved();
    } catch (error) {
      if (attempt !== this.generation) return;
      if (error instanceof Error && error.name === 'SessionExpired') { this.reset(); this.publish({ ...blank(), phase: 'blocked', problem: 401 }); return; }
      const status = error instanceof ProfileError ? error.status : 503;
      if (!save && status === 404) this.publish({ ...blank(), phase: 'ready', revision: 0 });
      else this.publish({ ...this.state, phase: save ? 'ready' : 'blocked', problem: status, saved: false });
    } finally { clearTimeout(timer); if (attempt === this.generation) this.pending = null; }
  }
}
