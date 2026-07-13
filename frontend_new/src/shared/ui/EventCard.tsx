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

export function EventCard({ event, matchScore, inAgenda, onOpen, onToggleAgenda, priority = false }: EventCardProps) {
  const CategoryIcon = categoryMeta(event.primaryCategory).icon;
  const summary = event.resumen || event.subtitulo || event.descripcion;

  return (
    <article
      data-testid="event-card"
      className="group relative flex flex-col overflow-hidden rounded-3xl border border-border/70 bg-card shadow-[0_10px_36px_rgba(15,10,5,0.07)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_18px_48px_rgba(15,10,5,0.14)]"
    >
      <button onClick={onOpen} className="block w-full text-left" aria-label={`Ver detalle de ${event.titulo}`}>
        <div className="relative aspect-[16/9] overflow-hidden">
          <CategoryCover
            src={event.imagen}
            alt=""
            category={event.primaryCategory}
            seed={event.id}
            priority={priority}
            className="transition-transform duration-500 group-hover:scale-[1.04]"
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent" />

          <div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-black/45 px-3 py-1 text-[11px] font-semibold text-white backdrop-blur-md">
              <CategoryIcon className="h-3 w-3" />
              {event.primaryCategory}
            </span>
          </div>

          {event.priceLabel ? (
            <span
              className={cn(
                'absolute right-3 top-3 rounded-full px-3 py-1 text-[11px] font-bold backdrop-blur-md',
                event.isFree ? 'bg-emerald-500/95 text-white' : 'bg-white/92 text-slate-900',
              )}
            >
              {event.priceLabel}
            </span>
          ) : null}

          <div className="absolute bottom-3 left-3 flex items-center gap-2">
            <span className="rounded-full bg-white/94 px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-slate-900">
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

      <div className="flex flex-1 flex-col gap-2.5 p-4">
        <button onClick={onOpen} className="block text-left">
          <h3 className="line-clamp-2 font-display text-[17px] font-bold leading-snug transition-colors group-hover:text-primary">
            {event.titulo}
          </h3>
        </button>

        {summary ? (
          <p className="line-clamp-2 text-[13px] leading-5 text-muted-foreground">{summary}</p>
        ) : null}

        <div className="mt-auto flex items-end justify-between gap-2 pt-1">
          <div className="min-w-0">
            <p className="flex items-center gap-1.5 text-[13px] text-muted-foreground">
              <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="line-clamp-1">{event.lugar || event.direccion || 'Madrid'}</span>
            </p>
            <p className="mt-0.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
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
              'inline-flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full border transition-colors',
              inAgenda
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border/80 bg-background text-muted-foreground hover:border-primary/50 hover:text-primary',
            )}
          >
            {inAgenda ? <BookmarkCheck className="h-4.5 w-4.5" /> : <Bookmark className="h-4.5 w-4.5" />}
          </button>
        </div>
      </div>
    </article>
  );
}
