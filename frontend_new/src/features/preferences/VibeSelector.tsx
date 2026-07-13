import { VIBE_META } from '../../domain/madplan/constants';
import type { VibeMode } from '../../domain/madplan/types';
import { cn } from '../../shared/lib/cn';

interface VibeSelectorProps {
  current: VibeMode;
  onSelect: (vibe: VibeMode) => void;
}

export function VibeSelector({ current, onSelect }: VibeSelectorProps) {
  return (
    <div className="scrollbar-none -mx-1 flex gap-2.5 overflow-x-auto px-1 py-1">
      {Object.entries(VIBE_META).map(([key, meta]) => {
        const active = current === key;
        return (
          <button
            key={key}
            onClick={() => onSelect(active ? null : (key as Exclude<VibeMode, null>))}
            aria-pressed={active}
            aria-label={`${meta.label}: ${meta.description}`}
            title={meta.description}
            className={cn(
              'inline-flex flex-shrink-0 items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-semibold transition-all duration-200',
              active
                ? 'border-primary bg-primary text-primary-foreground shadow-[0_8px_24px_rgba(0,0,0,0.14)]'
                : 'border-border/70 bg-card/75 text-foreground hover:-translate-y-0.5 hover:border-primary/50',
            )}
          >
            <span aria-hidden="true" className="text-base">{meta.emoji}</span>
            {meta.label}
          </button>
        );
      })}
    </div>
  );
}
