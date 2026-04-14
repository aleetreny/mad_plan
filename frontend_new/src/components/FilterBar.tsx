import { Filter, X } from 'lucide-react';
import { cn } from '../lib/utils';

interface Props {
  sources: string[];
  categories: string[];
  activeSource: string | null;
  activeCategory: string | null;
  onSourceChange: (s: string | null) => void;
  onCategoryChange: (c: string | null) => void;
  dateFilter: 'all' | 'today' | 'week' | 'month';
  onDateFilterChange: (d: 'all' | 'today' | 'week' | 'month') => void;
  freeOnly: boolean;
  onFreeOnlyChange: (v: boolean) => void;
}

export function FilterBar({
  sources, categories,
  activeSource, activeCategory,
  onSourceChange, onCategoryChange,
  dateFilter, onDateFilterChange,
  freeOnly, onFreeOnlyChange,
}: Props) {
  const hasFilters = activeSource || activeCategory || dateFilter !== 'all' || freeOnly;

  return (
    <div className="space-y-3">
      {/* Date + free */}
      <div className="flex flex-wrap gap-2">
        {(['all', 'today', 'week', 'month'] as const).map(d => (
          <button
            key={d}
            onClick={() => onDateFilterChange(d)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-full transition-colors",
              dateFilter === d ? "bg-foreground text-background" : "bg-muted text-muted-foreground hover:bg-muted/80"
            )}
          >
            {d === 'all' ? 'Todos' : d === 'today' ? 'Hoy' : d === 'week' ? 'Esta semana' : 'Este mes'}
          </button>
        ))}
        <button
          onClick={() => onFreeOnlyChange(!freeOnly)}
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded-full transition-colors",
            freeOnly ? "bg-green-500 text-white" : "bg-muted text-muted-foreground hover:bg-muted/80"
          )}
        >
          Gratis
        </button>
        {hasFilters && (
          <button
            onClick={() => { onSourceChange(null); onCategoryChange(null); onDateFilterChange('all'); onFreeOnlyChange(false); }}
            className="px-3 py-1.5 text-xs font-medium rounded-full bg-red-100 text-red-600 flex items-center gap-1"
          >
            <X className="w-3 h-3" /> Limpiar
          </button>
        )}
      </div>

      {/* Categories */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        <button
          onClick={() => onCategoryChange(null)}
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-colors flex-shrink-0",
            !activeCategory ? "bg-primary text-primary-foreground" : "bg-muted/50 text-muted-foreground hover:bg-muted"
          )}
        >
          Todas las categorías
        </button>
        {categories.slice(0, 12).map(c => (
          <button
            key={c}
            onClick={() => onCategoryChange(activeCategory === c ? null : c)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-colors flex-shrink-0",
              activeCategory === c ? "bg-primary text-primary-foreground" : "bg-muted/50 text-muted-foreground hover:bg-muted"
            )}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Sources */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        <Filter className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-1" />
        <button
          onClick={() => onSourceChange(null)}
          className={cn(
            "px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-colors flex-shrink-0",
            !activeSource ? "bg-secondary text-secondary-foreground" : "bg-muted/50 text-muted-foreground hover:bg-muted"
          )}
        >
          Todas las fuentes
        </button>
        {sources.map(s => (
          <button
            key={s}
            onClick={() => onSourceChange(activeSource === s ? null : s)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap transition-colors flex-shrink-0",
              activeSource === s ? "bg-secondary text-secondary-foreground" : "bg-muted/50 text-muted-foreground hover:bg-muted"
            )}
          >
            {s.replace(/_/g, ' ')}
          </button>
        ))}
      </div>
    </div>
  );
}
