import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CalendarDays, ExternalLink, MapPin, Share2, Ticket, X } from 'lucide-react';
import { formatLongDate, formatTime } from '../../domain/madplan/formatters';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { cn } from '../lib/cn';
import { MediaCover } from './MediaCover';

interface EventModalProps {
  event: MadPlanEvent | null;
  inAgenda: boolean;
  matchScore?: number;
  onClose: () => void;
  onToggleAgenda: () => void;
}

export function EventModal({ event, inAgenda, matchScore, onClose, onToggleAgenda }: EventModalProps) {
  const [feedback, setFeedback] = useState<string | null>(null);

  if (!event) return null;
  const activeEvent = event;

  async function handleShare() {
    const shareUrl = activeEvent.url || activeEvent.sourceLinks[0]?.url;
    if (!shareUrl) return;

    try {
      if (navigator.share) {
        await navigator.share({
          title: activeEvent.titulo,
          text: activeEvent.resumen || activeEvent.descripcion || activeEvent.primaryCategory,
          url: shareUrl,
        });
      } else {
        await navigator.clipboard.writeText(shareUrl);
        setFeedback('Enlace copiado al portapapeles.');
        window.setTimeout(() => setFeedback(null), 2000);
      }
    } catch {
      setFeedback('No se pudo compartir ahora mismo.');
      window.setTimeout(() => setFeedback(null), 2000);
    }
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-end justify-center bg-black/60 p-0 backdrop-blur-md sm:items-center sm:p-6" onClick={onClose}>
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 32 }}
          transition={{ duration: 0.24 }}
          className="relative max-h-[92vh] w-full max-w-4xl overflow-hidden rounded-t-[32px] bg-background shadow-[0_40px_90px_rgba(0,0,0,0.35)] sm:rounded-[32px]"
          onClick={(dialogEvent) => dialogEvent.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby="event-modal-title"
        >
          <button
            onClick={onClose}
            className="absolute right-4 top-4 z-10 inline-flex h-11 w-11 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur-md hover:bg-black/70"
            aria-label="Cerrar detalle del evento"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="grid gap-0 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="relative aspect-[16/11] min-h-[280px] lg:min-h-full">
              <MediaCover src={event.imagen} alt={event.titulo} className="h-full w-full object-cover" fallbackLabel={event.primaryCategory} />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
              <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
                <div className="mb-3 flex flex-wrap gap-2">
                  <span className="rounded-full bg-white/16 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]">{event.primaryCategory}</span>
                  <span className={cn(
                    'rounded-full px-3 py-1 text-[11px] font-semibold',
                    event.isFree ? 'bg-emerald-500 text-white' : 'bg-white/88 text-foreground',
                  )}>
                    {event.priceLabel}
                  </span>
                  {matchScore && matchScore > 0 ? (
                    <span className="rounded-full bg-primary px-3 py-1 text-[11px] font-semibold text-primary-foreground">
                      {matchScore}% encaje
                    </span>
                  ) : null}
                </div>
                <h2 id="event-modal-title" className="max-w-2xl text-3xl font-display font-bold leading-tight">
                  {event.titulo}
                </h2>
                {event.subtitulo ? <p className="mt-2 max-w-2xl text-sm text-white/85">{event.subtitulo}</p> : null}
              </div>
            </div>

            <div className="max-h-[92vh] overflow-y-auto p-6">
              <div className="space-y-5">
                <div className="grid gap-3 rounded-[28px] border border-border/70 bg-card/75 p-5">
                  <div className="flex items-start gap-3">
                    <CalendarDays className="mt-0.5 h-5 w-5 text-primary" />
                    <div>
                      <p className="text-sm font-semibold">{formatLongDate(event.primaryDate)}</p>
                      <p className="text-sm text-muted-foreground">{event.scheduleLabel}</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <MapPin className="mt-0.5 h-5 w-5 text-primary" />
                    <div>
                      <p className="text-sm font-semibold">{event.locationLabel}</p>
                      <p className="text-sm text-muted-foreground">{event.sourceLabel}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <h3 className="text-lg font-display font-bold">Por qué merece la pena</h3>
                  <p className="text-sm leading-7 text-muted-foreground">
                    {event.contenido || event.descripcion || event.resumen || 'Plan destacado dentro de la agenda cultural y de ocio de Madrid.'}
                  </p>
                </div>

                {event.sesiones && event.sesiones.length > 0 ? (
                  <div className="space-y-3">
                    <h3 className="text-lg font-display font-bold">Próximas sesiones</h3>
                    <div className="grid gap-2">
                      {event.sesiones.slice(0, 5).map((session) => (
                        <div key={`${event.id}-${session.fecha}-${session.datetime || 'all-day'}`} className="flex items-center justify-between rounded-2xl border border-border/70 bg-background/80 px-4 py-3 text-sm">
                          <span>{formatLongDate(session.datetime || session.fecha)}</span>
                          <span className="font-semibold text-primary">
                            {session.datetime ? formatTime(session.datetime) : 'Todo el día'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {event.sourceLinks.length > 0 ? (
                  <div className="space-y-3">
                    <h3 className="text-lg font-display font-bold">Dónde verlo o comprar</h3>
                    <div className="grid gap-2">
                      {event.sourceLinks.map((link) => (
                        <a
                          key={`${event.id}-${link.fuente}-${link.url}`}
                          href={link.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center justify-between rounded-2xl border border-border/70 bg-card/70 px-4 py-3 hover:bg-card"
                        >
                          <div>
                            <p className="text-sm font-semibold">{link.fuente.replace(/_/g, ' ')}</p>
                            <p className="text-xs text-muted-foreground">
                              {link.kind || 'detalle'} · {link.es_gratis ? 'Gratis' : event.priceLabel}
                            </p>
                          </div>
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      ))}
                    </div>
                  </div>
                ) : null}

                {event.categoriesList.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {event.categoriesList.slice(0, 6).map((category) => (
                      <span key={category} className="rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
                        {category}
                      </span>
                    ))}
                  </div>
                ) : null}

                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    onClick={onToggleAgenda}
                    className={cn(
                      'inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold',
                      inAgenda ? 'bg-foreground text-background' : 'bg-primary text-primary-foreground',
                    )}
                  >
                    <Ticket className="h-4 w-4" />
                    {inAgenda ? 'Guardado en agenda' : 'Añadir a mi agenda'}
                  </button>
                  <button
                    onClick={handleShare}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-border/80 px-5 py-3 text-sm font-semibold hover:bg-muted/60"
                  >
                    <Share2 className="h-4 w-4" />
                    Compartir plan
                  </button>
                </div>

                {feedback ? <p className="text-sm font-medium text-primary">{feedback}</p> : null}
                <p className="text-xs text-muted-foreground">
                  Actualizado para la navegación de hoy. {event.relativeLabel !== 'Sin fecha concreta' ? `Se celebra ${event.relativeLabel.toLocaleLowerCase('es-ES')}.` : 'La fecha exacta está por confirmar.'}
                </p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
