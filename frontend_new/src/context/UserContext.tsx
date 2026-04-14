import { createContext, useContext, useState, type ReactNode } from 'react';
import type { UserProfile, VibeMode } from '../types';

interface UserContextType {
  profile: UserProfile;
  addToAgenda: (eventId: string) => void;
  removeFromAgenda: (eventId: string) => void;
  isInAgenda: (eventId: string) => boolean;
  setVibe: (v: VibeMode) => void;
  setInterests: (i: string[]) => void;
  setAnsweredQuiz: (v: boolean) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

const STORAGE_KEY = 'madplan_user';

function loadProfile(): UserProfile {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { interests: [], answeredQuiz: false, agenda: [], vibe: null };
}

function saveProfile(p: UserProfile) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
}

export function UserProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile>(loadProfile);

  const update = (partial: Partial<UserProfile>) => {
    setProfile(prev => {
      const next = { ...prev, ...partial };
      saveProfile(next);
      return next;
    });
  };

  const addToAgenda = (id: string) => {
    if (!profile.agenda.includes(id)) update({ agenda: [...profile.agenda, id] });
  };
  const removeFromAgenda = (id: string) => {
    update({ agenda: profile.agenda.filter(x => x !== id) });
  };
  const isInAgenda = (id: string) => profile.agenda.includes(id);
  const setVibe = (v: VibeMode) => update({ vibe: v });
  const setInterests = (i: string[]) => update({ interests: i });
  const setAnsweredQuiz = (v: boolean) => update({ answeredQuiz: v });

  return (
    <UserContext.Provider value={{ profile, addToAgenda, removeFromAgenda, isInAgenda, setVibe, setInterests, setAnsweredQuiz }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error('useUser must be inside UserProvider');
  return ctx;
}
