import { createContext } from 'react';
import type { ThemeMode, TimeOfDay } from '../../../domain/madplan/types';

export interface ThemeContextValue {
  mode: ThemeMode;
  timeOfDay: TimeOfDay;
  setMode: (mode: ThemeMode) => void;
}

export const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

