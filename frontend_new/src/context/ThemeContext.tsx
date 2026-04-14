import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { TimeOfDay } from '../types';

interface ThemeContextType {
  timeOfDay: TimeOfDay;
  setTimeOfDay: (t: TimeOfDay) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

function getAutoTheme(): TimeOfDay {
  const h = new Date().getHours();
  if (h >= 6 && h < 12) return 'morning';
  if (h >= 12 && h < 18) return 'afternoon';
  if (h >= 18 && h < 22) return 'evening';
  return 'night';
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [timeOfDay, setTimeOfDay] = useState<TimeOfDay>(getAutoTheme);

  useEffect(() => {
    const interval = setInterval(() => {
      setTimeOfDay(prev => {
        const auto = getAutoTheme();
        return prev === auto ? prev : auto;
      });
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <ThemeContext.Provider value={{ timeOfDay, setTimeOfDay }}>
      <div className={`theme-${timeOfDay} min-h-screen bg-background text-foreground transition-colors duration-1000`}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be inside ThemeProvider');
  return ctx;
}
