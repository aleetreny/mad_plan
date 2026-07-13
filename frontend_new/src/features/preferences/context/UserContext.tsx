import { useState, type ReactNode } from 'react';
import type { UserProfile } from '../../../domain/madplan/types';
import { UserContext } from './user-context';

const STORAGE_KEY = 'madplan_user_profile_v3';

const DEFAULT_PROFILE: UserProfile = {
  interests: [],
  answeredQuiz: false,
  agenda: [],
  vibe: null,
  budget: null,
  companion: null,
  zones: [],
};

function loadProfile(): UserProfile {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PROFILE;
    const parsed = JSON.parse(raw) as Partial<UserProfile>;
    return {
      ...DEFAULT_PROFILE,
      ...parsed,
      agenda: Array.isArray(parsed.agenda) ? parsed.agenda : [],
      interests: Array.isArray(parsed.interests) ? parsed.interests : [],
      zones: Array.isArray(parsed.zones) ? parsed.zones : [],
    };
  } catch {
    return DEFAULT_PROFILE;
  }
}

export function UserProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile>(loadProfile);

  // Functional updates so several setters fired in the same event handler
  // (e.g. when the quiz finishes) never clobber each other.
  function update(partial: Partial<UserProfile> | ((current: UserProfile) => Partial<UserProfile>)) {
    setProfile((current) => {
      const patch = typeof partial === 'function' ? partial(current) : partial;
      const next = { ...current, ...patch };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // Ignore storage failures and keep the in-memory state.
      }
      return next;
    });
  }

  return (
    <UserContext.Provider
      value={{
        profile,
        addToAgenda: (eventId) => {
          update((current) =>
            current.agenda.includes(eventId) ? {} : { agenda: [...current.agenda, eventId] },
          );
        },
        removeFromAgenda: (eventId) => {
          update((current) => ({ agenda: current.agenda.filter((item) => item !== eventId) }));
        },
        isInAgenda: (eventId) => profile.agenda.includes(eventId),
        setVibe: (vibe) => update({ vibe }),
        setInterests: (interests) => update({ interests }),
        setAnsweredQuiz: (value) => update({ answeredQuiz: value }),
        setBudget: (budget) => update({ budget }),
        setCompanion: (companion) => update({ companion }),
        setZones: (zones) => update({ zones }),
      }}
    >
      {children}
    </UserContext.Provider>
  );
}
