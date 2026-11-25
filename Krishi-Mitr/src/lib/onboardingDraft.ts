/**
 * Lightweight client-side store that lets chat-extracted ONBOARD_PROFILE cards
 * pre-fill `S03_Profile.web.tsx` live when the farmer taps "Fill profile".
 */
import { useSyncExternalStore } from 'react';

export interface OnboardingDraft {
  name?: string;
  village?: string;
  district_id?: string;
  district_name?: string;
  version: number;
}

let draft: OnboardingDraft = { version: 0 };
const subs = new Set<() => void>();

export function setOnboardingDraft(patch: Omit<OnboardingDraft, 'version'>): void {
  draft = {
    ...(patch.name ? { name: patch.name } : draft.name ? { name: draft.name } : {}),
    ...(patch.village ? { village: patch.village } : draft.village ? { village: draft.village } : {}),
    ...(patch.district_id
      ? { district_id: patch.district_id }
      : draft.district_id
        ? { district_id: draft.district_id }
        : {}),
    ...(patch.district_name
      ? { district_name: patch.district_name }
      : draft.district_name
        ? { district_name: draft.district_name }
        : {}),
    version: draft.version + 1,
  };
  subs.forEach(fn => fn());
}

export function clearOnboardingDraft(): void {
  draft = { version: 0 };
  subs.forEach(fn => fn());
}

export function useOnboardingDraft(): OnboardingDraft {
  return useSyncExternalStore(
    fn => {
      subs.add(fn);
      return () => {
        subs.delete(fn);
      };
    },
    () => draft,
  );
}
