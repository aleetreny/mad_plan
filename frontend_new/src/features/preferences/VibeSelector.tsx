import { VIBE_META } from '../../domain/madplan/constants';
import type { VibeMode } from '../../domain/madplan/types';
import { cn } from '../../shared/lib/cn';

interface VibeSelectorProps {
  current: VibeMode;
  onSelect: (vibe: VibeMode) => void;
}

export function VibeSelector({ current, onSelect }: VibeSelectorProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {Object.entries(VIBE_META).map(([key, meta]) => (
        <button
          key={key}
          onClick={() => onSelect(current === key ? null : (key as Exclude<VibeMode, null>))}
          className={cn(
            'rounded-[28px] border border-border/70 bg-card/75 p-4 text-left transition-transform duration-300 hover:-translate-y-0.5 hover:border-primary/50',
            current === key ? 'border-primary bg-primary/10 shadow-[0_18px_45px_rgba(0,0,0,0.08)]' : '',
          )}
        >
          <div className="mb-3 text-2xl">{meta.emoji}</div>
          <p className="text-lg font-display font-bold">{meta.label}</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">{meta.description}</p>
        </button>
      ))}
    </div>
  );
}

