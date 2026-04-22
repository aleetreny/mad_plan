import { Filter, RotateCcw } from 'lucide-react';
import { SOURCE_LABELS, ZONES } from '../../domain/madplan/constants';
import type { DiscoveryDateFilter } from '../../domain/madplan/types';
import { cn } from '../../shared/lib/cn';

interface FilterBarProps {
  categories: string[];
  sources: string[];
  activeCategory: string | null;
  activeSource: string | null;
  dateFilter: DiscoveryDateFilter;
  freeOnly: boolean;
  activeZone: string | null;
  onCategoryChange: (value: string | null) => void;
  onSourceChange: (value: string | null) => void;
  onDateFilterChange: (value: DiscoveryDateFilter) => void;
  onFreeOnlyChange: (value: boolean) => void;
  onZoneChange: (value: string | null) => void;
  onClear: () => void;
  hasActiveFilters: boolean;
}

const DATE_FILTER_LABELS: Record<DiscoveryDateFilter, string> = {
  all: 'Todo',
  today: 'Hoy',
  weekend: 'Fin de semana',
  week: '7 días',
  month: 'Este mes',
};

export function FilterBar({
  categories,
  sources,
  activeCategory,
  activeSource,
  dateFilter,
  freeOnly,
  activeZone,
  onCategoryChange,
  onSourceChange,
  onDateFilterChange,
  onFreeOnlyChange,
  onZoneChange,
  onClear,
  hasActiveFilters,
}: FilterBarProps) {
  return (
    <div className="space-y-4 rounded-[30px] border border-border/70 bg-card/75 p-4 shadow-[0_16px_40px_rgba(0,0,0,0.06)] sm:p-5">
      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex items-center gap-2 rounded-full bg-secondary px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-secondary-foreground">
          <Filter className="h-3.5 w-3.5" />
          Filtros
        </div>
        {(Object.keys(DATE_FILTER_LABELS) as DiscoveryDateFilter[]).map((value) => (
          <button
            key={value}
            onClick={() => onDateFilterChange(value)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
              dateFilter === value ? 'bg-foreground text-background' : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            {DATE_FILTER_LABELS[value]}
          </button>
        ))}
        <button
          onClick={() => onFreeOnlyChange(!freeOnly)}
          className={cn(
            'rounded-full px-4 py-2 text-sm font-semibold transition-colors',
            freeOnly ? 'bg-emerald-500 text-white' : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground',
          )}
        >
          Gratis
        </button>
        {hasActiveFilters ? (
          <button onClick={onClear} className="inline-flex items-center gap-2 rounded-full border border-border/70 px-4 py-2 text-sm font-semibold hover:bg-muted/60">
            <RotateCcw className="h-4 w-4" />
            Limpiar
          </button>
        ) : null}
      </div>

      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Categorías</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => onCategoryChange(null)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap',
              activeCategory == null ? 'bg-primary text-primary-foreground' : 'bg-muted/60 text-muted-foreground hover:bg-muted',
            )}
          >
            Todas
          </button>
          {categories.slice(0, 12).map((category) => (
            <button
              key={category}
              onClick={() => onCategoryChange(activeCategory === category ? null : category)}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap',
                activeCategory === category ? 'bg-primary text-primary-foreground' : 'bg-muted/60 text-muted-foreground hover:bg-muted',
              )}
            >
              {category}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Fuentes</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => onSourceChange(null)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap',
              activeSource == null ? 'bg-secondary text-secondary-foreground' : 'bg-muted/60 text-muted-foreground hover:bg-muted',
            )}
          >
            Todas
          </button>
          {sources.map((source) => (
            <button
              key={source}
              onClick={() => onSourceChange(activeSource === source ? null : source)}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap',
                activeSource === source ? 'bg-secondary text-secondary-foreground' : 'bg-muted/60 text-muted-foreground hover:bg-muted',
              )}
            >
              {SOURCE_LABELS[source] || source}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Barrios y zonas</p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => onZoneChange(null)}
            className={cn(
              'rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap',
              activeZone == null ? 'bg-accent text-accent-foreground' : 'bg-muted/60 text-muted-foreground hover:bg-muted',
            )}
          >
            Toda la ciudad
          </button>
          {ZONES.map((zone) => (
            <button
              key={zone}
              onClick={() => onZoneChange(activeZone === zone ? null : zone)}
              className={cn(
                'rounded-full px-4 py-2 text-sm font-semibold whitespace-nowrap',
                activeZone === zone ? 'bg-accent text-accent-foreground' : 'bg-muted/60 text-muted-foreground hover:bg-muted',
              )}
            >
              {zone}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

