import { useTheme } from '../context/ThemeContext';
import { Sun, Cloud, Sunset, Moon, CalendarDays } from 'lucide-react';
import { cn } from '../lib/utils';

const themeIcons = {
  morning: Sun,
  afternoon: Cloud,
  evening: Sunset,
  night: Moon,
} as const;

const themeColors = {
  morning: 'text-amber-500',
  afternoon: 'text-green-500',
  evening: 'text-orange-500',
  night: 'text-indigo-400',
};

interface NavbarProps {
  onOpenAgenda: () => void;
  agendaCount: number;
}

export function Navbar({ onOpenAgenda, agendaCount }: NavbarProps) {
  const { timeOfDay } = useTheme();
  const Icon = themeIcons[timeOfDay];

  return (
    <nav className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center text-primary-foreground font-bold text-xl shadow-md">
            M
          </div>
          <div className="hidden sm:block">
            <h1 className="text-xl font-display font-bold leading-none">MadPlan</h1>
            <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">Madrid en vivo</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className={cn("flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-secondary text-secondary-foreground text-sm font-medium")}>
            <Icon className={cn("w-4 h-4", themeColors[timeOfDay])} />
            <span className="capitalize hidden sm:inline">{timeOfDay === 'morning' ? 'Mañana' : timeOfDay === 'afternoon' ? 'Tarde' : timeOfDay === 'evening' ? 'Atardecer' : 'Noche'}</span>
          </div>
          <button onClick={onOpenAgenda} className="relative p-2 rounded-full hover:bg-muted transition-colors" title="Tu agenda">
            <CalendarDays className="w-5 h-5" />
            {agendaCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center bg-primary text-primary-foreground text-[10px] font-bold rounded-full">{agendaCount}</span>
            )}
          </button>
        </div>
      </div>
    </nav>
  );
}
