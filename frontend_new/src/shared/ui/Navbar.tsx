import { CalendarDays, Compass, Map, MoonStar, SunMedium } from 'lucide-react';
import { THEME_META, THEME_MODES } from '../../domain/madplan/constants';
import type { ThemeMode } from '../../domain/madplan/types';
import { useTheme } from '../../features/theme/context/useTheme';
import { cn } from '../lib/cn';

interface NavbarProps {
  agendaCount: number;
  onOpenAgenda: () => void;
  onToggleView: () => void;
  isMapView: boolean;
}

const MODE_LABELS: Record<ThemeMode, string> = {
  auto: 'Auto',
  morning: 'Mañana',
  afternoon: 'Tarde',
  evening: 'Atardecer',
  night: 'Noche',
};

export function Navbar({ agendaCount, onOpenAgenda, onToggleView, isMapView }: NavbarProps) {
  const { mode, timeOfDay, setMode } = useTheme();
  const activeTheme = THEME_META[timeOfDay];

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-background/80 backdrop-blur-xl">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground">
        Saltar al contenido
      </a>
      <div className="mx-auto flex w-full max-w-[1440px] items-center justify-between gap-4 px-4 py-3 md:px-6">
        <div className="flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-primary text-xl font-black text-primary-foreground shadow-[0_16px_40px_rgba(0,0,0,0.18)]">
            M
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-primary/80">Madrid en vivo</p>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-display font-bold md:text-2xl">MadPlan</h1>
              <span className="hidden rounded-full bg-secondary px-2 py-1 text-[11px] font-medium text-secondary-foreground md:inline-flex">
                {activeTheme.accent}
              </span>
            </div>
          </div>
        </div>

        <div className="hidden min-w-0 flex-1 items-center justify-center md:flex">
          <div className="flex flex-wrap items-center gap-1 rounded-full border border-border/80 bg-card/60 p-1">
            {THEME_MODES.map((themeMode) => (
              <button
                key={themeMode}
                onClick={() => setMode(themeMode)}
                className={cn(
                  'rounded-full px-3 py-1.5 text-xs font-semibold transition-colors',
                  mode === themeMode ? 'bg-foreground text-background' : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
                )}
              >
                {MODE_LABELS[themeMode]}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 rounded-full bg-secondary/70 px-3 py-2 text-sm font-medium text-secondary-foreground md:flex">
            {timeOfDay === 'night' ? <MoonStar className="h-4 w-4" /> : <SunMedium className="h-4 w-4" />}
            {THEME_META[timeOfDay].label}
          </div>

          <button
            onClick={onToggleView}
            className="inline-flex items-center gap-2 rounded-full border border-border/80 bg-card/70 px-4 py-2 text-sm font-semibold hover:bg-muted/50"
            aria-label={isMapView ? 'Cambiar a vista lista' : 'Cambiar a vista mapa'}
          >
            {isMapView ? <Compass className="h-4 w-4" /> : <Map className="h-4 w-4" />}
            <span className="hidden sm:inline">{isMapView ? 'Vista lista' : 'Vista mapa'}</span>
          </button>

          <button
            onClick={onOpenAgenda}
            data-testid="open-agenda"
            className="relative inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-[0_16px_32px_rgba(0,0,0,0.18)] transition-transform hover:-translate-y-0.5"
          >
            <CalendarDays className="h-4 w-4" />
            <span className="hidden sm:inline">Mi agenda</span>
            <span className="rounded-full bg-white/16 px-2 py-0.5 text-xs">{agendaCount}</span>
          </button>
        </div>
      </div>
    </header>
  );
}

