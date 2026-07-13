import { Bookmark, LayoutGrid, Map, Newspaper } from 'lucide-react';
import { THEME_MODES } from '../../domain/madplan/constants';
import type { DiscoveryView, ThemeMode } from '../../domain/madplan/types';
import { useTheme } from '../../features/theme/context/useTheme';
import { cn } from '../lib/cn';

interface NavbarProps {
  view: DiscoveryView;
  onViewChange: (view: DiscoveryView) => void;
  agendaCount: number;
  onOpenAgenda: () => void;
}

const MODE_LABELS: Record<ThemeMode, string> = {
  auto: 'Auto',
  morning: 'Mañana',
  afternoon: 'Tarde',
  evening: 'Atardecer',
  night: 'Noche',
};

const MODE_ICONS: Record<ThemeMode, string> = {
  auto: '✨',
  morning: '🌅',
  afternoon: '☀️',
  evening: '🌇',
  night: '🌙',
};

const VIEW_TABS: Array<{ key: DiscoveryView; label: string; icon: typeof Map }> = [
  { key: 'list', label: 'Planes', icon: LayoutGrid },
  { key: 'map', label: 'Mapa', icon: Map },
  { key: 'news', label: 'Noticias', icon: Newspaper },
];

export function Navbar({ view, onViewChange, agendaCount, onOpenAgenda }: NavbarProps) {
  const { mode, setMode } = useTheme();

  function cycleMode() {
    const index = THEME_MODES.indexOf(mode);
    setMode(THEME_MODES[(index + 1) % THEME_MODES.length]);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/85 backdrop-blur-xl">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Saltar al contenido
      </a>
      <div className="mx-auto flex w-full max-w-[1280px] items-center justify-between gap-2 px-3 py-3 sm:gap-3 sm:px-4 md:px-6">
        <button
          onClick={() => onViewChange('list')}
          className="flex items-center gap-2.5"
          aria-label="Ir a la portada de MadPlan"
        >
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary font-display text-lg font-black text-primary-foreground shadow-[0_8px_24px_rgba(0,0,0,0.16)]">
            M
          </div>
          <div className="hidden text-left min-[440px]:block">
            <h1 className="font-display text-lg font-bold leading-none md:text-xl">MadPlan</h1>
            <p className="mt-0.5 hidden text-[10px] font-semibold uppercase tracking-[0.22em] text-muted-foreground sm:block">
              Planes en Madrid
            </p>
          </div>
        </button>

        <nav
          aria-label="Secciones"
          className="flex items-center gap-1 rounded-full border border-border/70 bg-card/70 p-1"
        >
          {VIEW_TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => onViewChange(key)}
              aria-current={view === key ? 'page' : undefined}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold transition-colors md:px-4',
                view === key
                  ? 'bg-foreground text-background shadow-sm'
                  : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button
            onClick={cycleMode}
            title={`Ambiente: ${MODE_LABELS[mode]} (clic para cambiar)`}
            aria-label={`Cambiar ambiente visual, actual ${MODE_LABELS[mode]}`}
            className="inline-flex h-10 w-10 items-center justify-center gap-1.5 rounded-full border border-border/70 bg-card/70 text-sm font-semibold hover:bg-muted/50 lg:w-auto lg:px-3"
          >
            <span aria-hidden="true">{MODE_ICONS[mode]}</span>
            <span className="hidden lg:inline">{MODE_LABELS[mode]}</span>
          </button>

          <button
            onClick={onOpenAgenda}
            data-testid="open-agenda"
            className="relative inline-flex h-10 items-center gap-1.5 rounded-full bg-primary px-3 text-sm font-semibold text-primary-foreground shadow-[0_8px_24px_rgba(0,0,0,0.16)] transition-transform hover:-translate-y-0.5 sm:gap-2 sm:px-4"
          >
            <Bookmark className="h-4 w-4" />
            <span className="hidden md:inline">Mi agenda</span>
            {agendaCount > 0 ? (
              <span className="rounded-full bg-white/20 px-1.5 py-0.5 text-xs font-bold sm:px-2">{agendaCount}</span>
            ) : null}
          </button>
        </div>
      </div>
    </header>
  );
}
