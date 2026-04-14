import { useTheme } from '../context/ThemeContext';
import { Sun, Cloud, Sunset, Moon } from 'lucide-react';
import type { TimeOfDay } from '../types';

const items: { key: TimeOfDay; icon: typeof Sun; label: string; color: string }[] = [
  { key: 'morning', icon: Sun, label: 'Mañana', color: 'text-amber-500' },
  { key: 'afternoon', icon: Cloud, label: 'Tarde', color: 'text-green-500' },
  { key: 'evening', icon: Sunset, label: 'Atardecer', color: 'text-orange-500' },
  { key: 'night', icon: Moon, label: 'Noche', color: 'text-indigo-400' },
];

export function ThemeToggle() {
  const { timeOfDay, setTimeOfDay } = useTheme();
  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="flex flex-col gap-2 p-2 rounded-2xl bg-background/80 backdrop-blur-md border shadow-2xl">
        {items.map(({ key, icon: Icon, label, color }) => (
          <button
            key={key}
            onClick={() => setTimeOfDay(key)}
            className={`p-2 rounded-xl transition-colors ${timeOfDay === key ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}
            title={label}
          >
            <Icon className={`w-4 h-4 ${timeOfDay === key ? '' : color}`} />
          </button>
        ))}
      </div>
    </div>
  );
}
