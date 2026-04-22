import type { ReactNode } from 'react';
import { UserProvider } from '../../features/preferences/context/UserContext';
import { ThemeProvider } from '../../features/theme/context/ThemeContext';

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <UserProvider>{children}</UserProvider>
    </ThemeProvider>
  );
}

