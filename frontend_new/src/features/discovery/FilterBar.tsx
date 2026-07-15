import { ChevronDown, RotateCcw } from 'lucide-react';
import { categoryMeta, SOURCE_LABELS, ZONES } from '../../domain/madplan/constants';
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
  all: 'Cuando sea',
  today: 'Hoy',
  tomorrow: 'Mañana',
  weekend: 'Finde',
  week: '7 días',
  month: 'Este mes',
};

function SelectPill({
  value,
  placeholder,
  options,
  onChange,
  labelMap,
}: {
  value: string | null;
  placeholder: string;
  options: string[];
  onChange: (value: string | null) => void;
  labelMap?: Record<string, string>;
}) {
  return (
    <label className={cn(
      'relative inline-flex h-9 cursor-pointer items-center rounded-full border text-sm font-semibold transition-colors',
      value
        ? 'border-primary/50 bg-primary/10 text-primary'
        : 'border-border/80 bg-card/70 text-muted-foreground hover:bg-muted/50',
    )}>
      <span className="sr-only">{placeholder}</span>
      <select
        value={value || ''}
        onChange={(event) => onChange(event.target.value || null)}
        className="h-full cursor-pointer appearance-none rounded-full bg-transparent pl-4 pr-8 text-sm font-semibold outline-none"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {labelMap?.[option] || option}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 h-3.5 w-3.5" />
    </label>
  );
}

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
    <div className="space-y-3 rounded-3xl border border-border/70 bg-card/75 p-4 shadow-[0_8px_28px_rgba(15,10,5,0.05)]">
      <div className="flex flex-wrap items-center gap-2">
        {(Object.keys(DATE_FILTER_LABELS) as DiscoveryDateFilter[]).map((value) => (
          <button
            key={value}
            onClick={() => onDateFilterChange(value)}
            aria-pressed={dateFilter === value}
            className={cn(
              'h-9 rounded-full px-4 text-sm font-semibold transition-colors',
              dateFilter === value
                ? 'bg-foreground text-background'
                : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground',
            )}
          >
            {DATE_FILTER_LABELS[value]}
          </button>
        ))}

        <button
          onClick={() => onFreeOnlyChange(!freeOnly)}
          aria-pressed={freeOnly}
          className={cn(
            'h-9 rounded-full px-4 text-sm font-semibold transition-colors',
            freeOnly ? 'bg-emerald-600 text-white' : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground',
          )}
        >
          Gratis
        </button>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <SelectPill
            value={activeZone}
            placeholder="Toda la ciudad"
            options={ZONES.map((zone) => zone.name)}
            onChange={onZoneChange}
          />
          <SelectPill
            value={activeSource}
            placeholder="Todas las fuentes"
            options={sources}
            labelMap={SOURCE_LABELS}
            onChange={onSourceChange}
          />
          {hasActiveFilters ? (
            <button
              onClick={onClear}
              className="inline-flex h-9 items-center gap-1.5 rounded-full border border-border/80 px-3.5 text-sm font-semibold text-muted-foreground hover:bg-muted/60 hover:text-foreground"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Limpiar
            </button>
          ) : null}
        </div>
      </div>

      <div className="scrollbar-none -mx-1 flex gap-2 overflow-x-auto px-1 pb-0.5">
        <button
          onClick={() => onCategoryChange(null)}
          className={cn(
            'h-9 flex-shrink-0 whitespace-nowrap rounded-full px-4 text-sm font-semibold transition-colors',
            activeCategory == null
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground',
          )}
        >
          Todo
        </button>
        {categories.map((category) => {
          const Icon = categoryMeta(category).icon;
          return (
            <button
              key={category}
              onClick={() => onCategoryChange(activeCategory === category ? null : category)}
              aria-pressed={activeCategory === category}
              className={cn(
                'inline-flex h-9 flex-shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-4 text-sm font-semibold transition-colors',
                activeCategory === category
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground',
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {category}
            </button>
          );
        })}
      </div>
    </div>
  );
}
