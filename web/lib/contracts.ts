/** app.v1: Kim-owned application contract. This is not Vincent's procedure schema. */
import type { ProfileFields } from './profile.generated';
export { PROFILE_LIMITS, type ProfileFields } from './profile.generated';
export const APPLICATION_CONTRACT_VERSION = 'app.v1' as const;
export type ProfileRecord = { profile_id: string; revision: number; fields: ProfileFields };
export type ProfileUpdate = { expected_revision: number; fields: ProfileFields };
export type FormRenderRequest = {
  values: ProfileFields; revision: number; template_version: string; acknowledged: boolean;
};
export const EMPTY_PROFILE: ProfileFields = {
  full_name: null, date_of_birth: null, nationality: null, address: null, phone_number: null, email: null,
};
