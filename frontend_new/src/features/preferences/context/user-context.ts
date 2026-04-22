import { createContext } from 'react';
import type { BudgetPreference, CompanionMode, UserProfile, VibeMode } from '../../../domain/madplan/types';

export interface UserContextValue {
  profile: UserProfile;
  addToAgenda: (eventId: string) => void;
  removeFromAgenda: (eventId: string) => void;
  isInAgenda: (eventId: string) => boolean;
  setVibe: (vibe: VibeMode) => void;
  setInterests: (interests: string[]) => void;
  setAnsweredQuiz: (value: boolean) => void;
  setBudget: (budget: BudgetPreference) => void;
  setCompanion: (companion: CompanionMode) => void;
  setZones: (zones: string[]) => void;
}

export const UserContext = createContext<UserContextValue | undefined>(undefined);

