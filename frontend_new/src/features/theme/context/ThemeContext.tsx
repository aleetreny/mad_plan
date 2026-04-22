import { useEffect, useState, type ReactNode } from 'react';
import { getCurrentThemeTime } from '../../../domain/madplan/formatters';
import type { ThemeMode, TimeOfDay } from '../../../domain/madplan/types';
import { ThemeContext } from './theme-context';

const STORAGE_KEY = 'madplan_theme_mode';

function resolveTheme(mode: ThemeMode): TimeOfDay {
  return mode === 'auto' ? getCurrentThemeTime() : mode;
}

function loadInitialMode(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'auto' || stored === 'morning' || stored === 'afternoon' || stored === 'evening' || stored === 'night') {
      return stored;
    }
  } catch {
    return 'auto';
  }

  return 'auto';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(loadInitialMode);
  const [timeOfDay, setTimeOfDay] = useState<TimeOfDay>(() => resolveTheme(loadInitialMode()));

  useEffect(() => {
    setTimeOfDay(resolveTheme(mode));
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // Ignore write failures in private browsing or restricted environments.
    }
  }, [mode]);

  useEffect(() => {
    if (mode !== 'auto') return undefined;

    const interval = window.setInterval(() => {
      setTimeOfDay(getCurrentThemeTime());
    }, 60_000);

    return () => {
      window.clearInterval(interval);
    };
  }, [mode]);

  return (
    <ThemeContext.Provider value={{ mode, timeOfDay, setMode: setModeState }}>
      <div className={`theme-${timeOfDay} app-shell min-h-screen bg-background text-foreground transition-colors duration-700`}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
}
