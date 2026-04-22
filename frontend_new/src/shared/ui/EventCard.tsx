import { ExternalLink, MapPin, Plus, Star } from 'lucide-react';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { cn } from '../lib/cn';
import { MediaCover } from './MediaCover';

interface EventCardProps {
  event: MadPlanEvent;
  matchScore?: number;
  inAgenda: boolean;
  onOpen: () => void;
  onToggleAgenda: () => void;
  priority?: boolean;
}

export function EventCard({ event, matchScore, inAgenda, onOpen, onToggleAgenda, priority = false }: EventCardProps) {
  const primaryLink = event.url || event.sourceLinks[0]?.url;

  return (
    <article
      data-testid="event-card"
      className="group overflow-hidden rounded-[28px] border border-border/70 bg-card/80 shadow-[0_24px_60px_rgba(0,0,0,0.08)] transition-transform duration-300 hover:-translate-y-1 hover:shadow-[0_24px_70px_rgba(0,0,0,0.16)]"
    >
      <button onClick={onOpen} className="block w-full text-left">
        <div className="relative aspect-[16/10] overflow-hidden">
          <MediaCover
            src={event.imagen}
            alt={event.titulo}
            priority={priority}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            fallbackLabel={event.primaryCategory}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent" />
          <div className="absolute left-3 top-3 flex flex-wrap gap-2">
            <span className="rounded-full bg-black/50 px-3 py-1 text-[11px] font-semibold text-white backdrop-blur-md">
              {event.primaryCategory}
            </span>
            <span className={cn(
              'rounded-full px-3 py-1 text-[11px] font-semibold backdrop-blur-md',
              event.isFree ? 'bg-emerald-500 text-white' : 'bg-white/90 text-foreground',
            )}>
              {event.priceLabel}
            </span>
          </div>
        </div>
      </button>

      <div className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="mb-1 text-xs font-semibold uppercase tracking-[0.2em] text-primary/85">{event.scheduleLabel}</p>
            <button onClick={onOpen} className="block text-left">
              <h3 className="text-lg font-display font-bold leading-tight transition-colors group-hover:text-primary">
                {event.titulo}
              </h3>
            </button>
          </div>
          {matchScore && matchScore > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-secondary px-2.5 py-1 text-[11px] font-semibold text-secondary-foreground">
              <Star className="h-3 w-3" />
              {matchScore}%
            </span>
          ) : null}
        </div>

        <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
          {event.resumen || event.descripcion || event.subtitulo || 'Plan destacado en Madrid.'}
        </p>

        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4 flex-shrink-0" />
              <span className="line-clamp-1">{event.locationLabel}</span>
            </p>
            <p className="mt-1 text-xs font-medium text-muted-foreground">{event.sourceLabel}</p>
          </div>

          <div className="flex items-center gap-2">
            {primaryLink ? (
              <a
                href={primaryLink}
                target="_blank"
                rel="noreferrer"
                onClick={(eventRef) => eventRef.stopPropagation()}
                className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-border/80 bg-background/80 hover:bg-muted/60"
                aria-label="Abrir evento original"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            ) : null}
            <button
              onClick={onToggleAgenda}
              aria-pressed={inAgenda}
              className={cn(
                'inline-flex h-11 items-center justify-center rounded-full px-4 text-sm font-semibold transition-colors',
                inAgenda ? 'bg-foreground text-background' : 'bg-primary text-primary-foreground',
              )}
            >
              <Plus className="mr-2 h-4 w-4" />
              {inAgenda ? 'Guardado' : 'Agenda'}
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

