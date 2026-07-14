import { Bookmark, BookmarkCheck, MapPin, Star } from 'lucide-react';
import { categoryMeta } from '../../domain/madplan/constants';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { cn } from '../lib/cn';
import { CategoryCover } from './CategoryCover';

interface EventCardProps {
  event: MadPlanEvent;
  matchScore?: number;
  inAgenda: boolean;
  onOpen: () => void;
  onToggleAgenda: () => void;
  priority?: boolean;
}

/**
 * Responsive card: compact horizontal row on phones (thumbnail + text),
 * full vertical card with cover from `sm` upwards.
 */
export function EventCard({ event, matchScore, inAgenda, onOpen, onToggleAgenda, priority = false }: EventCardProps) {
  const CategoryIcon = categoryMeta(event.primaryCategory).icon;
  const summary = event.resumen || event.subtitulo || event.descripcion;

  return (
    <article
      data-testid="event-card"
      className="group relative flex overflow-hidden rounded-2xl border border-border/70 bg-card shadow-[0_6px_24px_rgba(15,10,5,0.06)] transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_14px_40px_rgba(15,10,5,0.13)] sm:flex-col sm:rounded-3xl"
    >
      <button
        onClick={onOpen}
        className="relative block w-[112px] flex-shrink-0 self-stretch sm:w-full"
        aria-label={`Ver detalle de ${event.titulo}`}
      >
        <div className="relative h-full min-h-[122px] overflow-hidden sm:aspect-[16/9] sm:h-auto sm:min-h-0">
          <CategoryCover
            src={event.imagen}
            alt=""
            category={event.primaryCategory}
            seed={event.id}
            priority={priority}
            iconSize={30}
            className="absolute inset-0 transition-transform duration-500 group-hover:scale-[1.04] sm:static"
          />
          <div className="pointer-events-none absolute inset-0 hidden bg-gradient-to-t from-black/55 via-black/10 to-transparent sm:block" />

          <div className="absolute left-3 top-3 hidden flex-wrap gap-1.5 sm:flex">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-black/45 px-2.5 py-1 text-[11px] font-semibold text-white backdrop-blur-md">
              <CategoryIcon className="h-3 w-3" />
              {event.primaryCategory}
            </span>
          </div>

          {event.priceLabel ? (
            <span
              className={cn(
                'absolute right-3 top-3 hidden rounded-full px-2.5 py-1 text-[11px] font-bold backdrop-blur-md sm:inline-block',
                event.isFree ? 'bg-emerald-500/95 text-white' : 'bg-white/92 text-slate-900',
              )}
            >
              {event.priceLabel}
            </span>
          ) : null}

          <div className="absolute bottom-3 left-3 hidden items-center gap-2 sm:flex">
            <span className="rounded-full bg-white/94 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-slate-900">
              {event.scheduleLabel}
            </span>
            {matchScore && matchScore > 20 ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/95 px-2.5 py-1 text-[11px] font-bold text-primary-foreground">
                <Star className="h-3 w-3 fill-current" />
                {matchScore}%
              </span>
            ) : null}
          </div>
        </div>
      </button>

      <div className="flex min-w-0 flex-1 flex-col gap-1.5 p-3 sm:gap-2.5 sm:p-4">
        {/* Línea de fecha/precio solo en el layout compacto móvil */}
        <p className="text-[11px] font-bold uppercase tracking-wide text-primary sm:hidden">
          {event.scheduleLabel}
          {event.priceLabel ? (
            <span className={cn('ml-2 normal-case tracking-normal', event.isFree ? 'text-emerald-600' : 'text-muted-foreground')}>
              {event.priceLabel}
            </span>
          ) : null}
        </p>

        <button onClick={onOpen} className="block text-left">
          <h3 className="line-clamp-2 font-display text-[15px] font-bold leading-snug transition-colors group-hover:text-primary sm:text-[16px]">
            {event.titulo}
          </h3>
        </button>

        {summary ? (
          <p className="line-clamp-2 text-[13px] leading-5 text-muted-foreground max-sm:hidden">{summary}</p>
        ) : null}

        <div className="mt-auto flex items-end justify-between gap-2 pt-0.5 sm:pt-1">
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-[12px] text-muted-foreground sm:text-[13px]">
              <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="line-clamp-1">{event.lugar || event.direccion || 'Madrid'}</span>
            </p>
            <p className="mt-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/70 sm:text-[11px]">
              {event.sourceLabel}
              {event.fuentes_relacionadas && event.fuentes_relacionadas.length > 1
                ? ` +${event.fuentes_relacionadas.length - 1}`
                : ''}
            </p>
          </div>

          <button
            onClick={onToggleAgenda}
            aria-pressed={inAgenda}
            aria-label={inAgenda ? 'Quitar de mi agenda' : 'Guardar en mi agenda'}
            className={cn(
              'inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border transition-colors sm:h-10 sm:w-10',
              inAgenda
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border/80 bg-background text-muted-foreground hover:border-primary/50 hover:text-primary',
            )}
          >
            {inAgenda ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </article>
  );
}
