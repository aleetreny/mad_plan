import { motion } from 'framer-motion';
import { Palette, PartyPopper, TreePalm, UtensilsCrossed, Mountain, Baby } from 'lucide-react';
import type { VibeMode } from '../types';
import { cn } from '../lib/utils';

const vibes: { key: VibeMode & string; icon: typeof Palette; label: string; emoji: string; desc: string }[] = [
  { key: 'cultural', icon: Palette, label: 'Cultural', emoji: '🎨', desc: 'Museos, expos y teatro' },
  { key: 'fiesta', icon: PartyPopper, label: 'Fiesta', emoji: '🎉', desc: 'Conciertos y vida nocturna' },
  { key: 'relax', icon: TreePalm, label: 'Relax', emoji: '🧘', desc: 'Parques y bienestar' },
  { key: 'foodie', icon: UtensilsCrossed, label: 'Foodie', emoji: '🍽️', desc: 'Gastronomía y mercados' },
  { key: 'aventura', icon: Mountain, label: 'Aventura', emoji: '🏃', desc: 'Deporte y aire libre' },
  { key: 'familiar', icon: Baby, label: 'Familiar', emoji: '👨‍👩‍👧', desc: 'Planes con niños' },
];

interface Props {
  current: VibeMode;
  onSelect: (v: VibeMode) => void;
}

export function VibeSelector({ current, onSelect }: Props) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {vibes.map(({ key, label, emoji, desc }) => (
        <motion.button
          key={key}
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onSelect(current === key ? null : key)}
          className={cn(
            "flex flex-col items-center gap-2 p-4 rounded-2xl border-2 transition-all text-center",
            current === key
              ? "border-primary bg-primary/10 shadow-lg shadow-primary/10"
              : "border-border hover:border-primary/40 bg-card/50"
          )}
        >
          <span className="text-2xl">{emoji}</span>
          <span className="font-bold text-sm">{label}</span>
          <span className="text-[10px] text-muted-foreground leading-tight">{desc}</span>
        </motion.button>
      ))}
    </div>
  );
}
