import { useEffect, useRef, useState } from 'react';
import {
  Bookmark,
  BookmarkCheck,
  CalendarDays,
  CalendarPlus,
  ExternalLink,
  MapPin,
  Navigation,
  Share2,
  X,
} from 'lucide-react';
import { formatLongDate, formatTime } from '../../domain/madplan/formatters';
import { sourceLabel } from '../../domain/madplan/formatters';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { cn } from '../lib/cn';
import { CategoryCover } from './CategoryCover';

interface EventModalProps {
  event: MadPlanEvent | null;
  inAgenda: boolean;
  matchScore?: number;
  onClose: () => void;
  onToggleAgenda: () => void;
}

function directionsUrl(event: MadPlanEvent): string | null {
  if (event.hasCoordinates && event.latitud != null && event.longitud != null) {
    return `https://www.google.com/maps/search/?api=1&query=${event.latitud},${event.longitud}`;
  }
  const query = [event.lugar, event.direccion, 'Madrid'].filter(Boolean).join(', ');
  if (!query || query === 'Madrid') return null;
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

function googleCalendarUrl(event: MadPlanEvent): string | null {
  if (!event.primaryDate) return null;
  const start = event.primaryDate;
  const end = new Date(start.getTime() + 2 * 3600000);
  const fmt = (date: Date) =>
    `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}` +
    `T${String(date.getHours()).padStart(2, '0')}${String(date.getMinutes()).padStart(2, '0')}00`;
  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.titulo,
    dates: `${fmt(start)}/${fmt(end)}`,
    details: (event.resumen || event.descripcion || '').slice(0, 400) + (event.url ? `\n${event.url}` : ''),
    location: [event.lugar, event.direccion].filter(Boolean).join(', ') || 'Madrid',
  });
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

const LINK_KIND_LABELS: Record<string, string> = {
  compra: 'Comprar entradas',
  detalle: 'Ver detalle',
  editorial: 'Artículo',
};

export function EventModal({ event, inAgenda, matchScore, onClose, onToggleAgenda }: EventModalProps) {
  const [feedback, setFeedback] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!event) return;
    function onKeyDown(keyEvent: KeyboardEvent) {
      if (keyEvent.key === 'Escape') {
        onClose();
        return;
      }
      // Focus trap: Tab circula dentro del diálogo, nunca hacia la página.
      if (keyEvent.key === 'Tab' && dialogRef.current) {
        const focusables = dialogRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (focusables.length === 0) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement;
        if (keyEvent.shiftKey && (active === first || active === dialogRef.current)) {
          keyEvent.preventDefault();
          last.focus();
        } else if (!keyEvent.shiftKey && active === last) {
          keyEvent.preventDefault();
          first.focus();
        } else if (active && !dialogRef.current.contains(active)) {
          keyEvent.preventDefault();
          first.focus();
        }
      }
    }
    window.addEventListener('keydown', onKeyDown);
    document.body.style.overflow = 'hidden';
    // Mueve el foco al diálogo para que Escape y el lector de pantalla
    // funcionen sin un clic previo.
    dialogRef.current?.focus({ preventScroll: true });
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
    };
  }, [event, onClose]);

  if (!event) return null;
  const activeEvent = event;
  const maps = directionsUrl(activeEvent);
  const calendar = googleCalendarUrl(activeEvent);
  const body = activeEvent.descripcion || activeEvent.resumen;

  async function handleShare() {
    // Se comparte el plan DENTRO de madplan (deep-link ?plan=…), no la web
    // de la fuente: quien recibe el enlace aterriza aquí con el detalle abierto.
    const params = new URLSearchParams();
    params.set('plan', activeEvent.id);
    const shareUrl = `${window.location.origin}${window.location.pathname}?${params.toString()}`;

    try {
      if (navigator.share) {
        await navigator.share({
          title: `${activeEvent.titulo} · madplan`,
          text: activeEvent.resumen || activeEvent.primaryCategory,
          url: shareUrl,
        });
      } else {
        await navigator.clipboard.writeText(shareUrl);
        setFeedback('Enlace copiado: mándaselo a quien quieras.');
        window.setTimeout(() => setFeedback(null), 2500);
      }
    } catch {
      setFeedback('No se pudo compartir ahora mismo.');
      window.setTimeout(() => setFeedback(null), 2000);
    }
  }

  return (
    <>
      <div
        className="anim-fade-in fixed inset-0 z-[1200] flex items-end justify-center bg-black/60 p-0 backdrop-blur-md sm:items-center sm:p-6"
        onClick={onClose}
      >
        <div
          ref={dialogRef}
          tabIndex={-1}
          className="anim-fade-up relative max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-t-3xl bg-background shadow-[0_40px_90px_rgba(0,0,0,0.35)] outline-none sm:rounded-3xl"
          onClick={(dialogEvent) => dialogEvent.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby="event-modal-title"
        >
          <button
            onClick={onClose}
            className="absolute right-4 top-4 z-10 inline-flex h-10 w-10 items-center justify-center rounded-full bg-black/55 text-white backdrop-blur-md hover:bg-black/70"
            aria-label="Cerrar detalle del evento"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="relative aspect-[16/8] min-h-[220px] overflow-hidden">
            <CategoryCover
              src={activeEvent.imagen}
              alt=""
              category={activeEvent.primaryCategory}
              seed={activeEvent.id}
              iconSize={64}
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-5 text-white sm:p-6">
              <div className="mb-2.5 flex flex-wrap gap-2">
                <span className="rounded-full bg-white/18 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] backdrop-blur-sm">
                  {activeEvent.primaryCategory}
                </span>
                {activeEvent.priceLabel ? (
                  <span
                    className={cn(
                      'rounded-full px-3 py-1 text-[11px] font-bold',
                      activeEvent.isFree ? 'bg-emerald-500 text-white' : 'bg-white/90 text-slate-900',
                    )}
                  >
                    {activeEvent.priceLabel}
                  </span>
                ) : null}
                {matchScore && matchScore > 20 ? (
                  <span className="rounded-full bg-primary px-3 py-1 text-[11px] font-bold text-primary-foreground">
                    {matchScore}% para ti
                  </span>
                ) : null}
              </div>
              <h2 id="event-modal-title" className="max-w-2xl font-display text-2xl font-bold leading-tight sm:text-3xl">
                {activeEvent.titulo}
              </h2>
              {activeEvent.subtitulo ? (
                <p className="mt-1.5 max-w-2xl text-sm text-white/85">{activeEvent.subtitulo}</p>
              ) : null}
            </div>
          </div>

          <div className="space-y-5 p-5 sm:p-6">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex items-start gap-3 rounded-2xl border border-border/70 bg-card/75 p-4">
                <CalendarDays className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold">
                    {activeEvent.isOngoing
                      ? `En curso${activeEvent.endDate ? ` · hasta el ${formatLongDate(activeEvent.endDate)}` : ''}`
                      : formatLongDate(activeEvent.primaryDate)}
                  </p>
                  <p className="text-sm text-muted-foreground">{activeEvent.scheduleLabel}</p>
                </div>
              </div>
              <div className="flex items-start gap-3 rounded-2xl border border-border/70 bg-card/75 p-4">
                <MapPin className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold">{activeEvent.lugar || 'Madrid'}</p>
                  {activeEvent.direccion ? (
                    <p className="text-sm text-muted-foreground">{activeEvent.direccion}</p>
                  ) : null}
                  {maps ? (
                    <a
                      href={maps}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline"
                    >
                      <Navigation className="h-3.5 w-3.5" />
                      Cómo llegar
                    </a>
                  ) : null}
                </div>
              </div>
            </div>

            {body ? (
              <div className="space-y-2">
                <h3 className="font-display text-lg font-bold">El plan</h3>
                <p className="text-sm leading-7 text-muted-foreground">{body}</p>
              </div>
            ) : null}

            {activeEvent.sesiones && activeEvent.sesiones.length > 1 ? (
              <div className="space-y-2">
                <h3 className="font-display text-lg font-bold">Próximas fechas</h3>
                <div className="grid gap-2 sm:grid-cols-2">
                  {activeEvent.sesiones.slice(0, 6).map((session) => (
                    <div
                      key={`${activeEvent.id}-${session.fecha}-${session.datetime || 'all-day'}`}
                      className="flex items-center justify-between rounded-xl border border-border/70 bg-background/80 px-3.5 py-2.5 text-sm"
                    >
                      <span>{formatLongDate(session.datetime || session.fecha)}</span>
                      <span className="font-semibold text-primary">
                        {session.datetime ? formatTime(session.datetime) : ''}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {activeEvent.sourceLinks.length > 0 ? (
              <div className="space-y-2">
                <h3 className="font-display text-lg font-bold">Entradas e info oficial</h3>
                <div className="grid gap-2">
                  {activeEvent.sourceLinks.map((link) => (
                    <a
                      key={`${activeEvent.id}-${link.fuente}-${link.url}`}
                      href={link.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-card/70 px-4 py-3 transition-colors hover:border-primary/40 hover:bg-card"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-semibold">
                          {LINK_KIND_LABELS[link.kind || 'detalle'] || 'Ver detalle'} · {sourceLabel(link.fuente)}
                        </p>
                        <p className="line-clamp-1 text-xs text-muted-foreground">{link.url.replace(/^https?:\/\//, '')}</p>
                      </div>
                      <ExternalLink className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                    </a>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="flex flex-col gap-2.5 sm:flex-row">
              <button
                onClick={onToggleAgenda}
                className={cn(
                  'inline-flex h-12 w-full items-center justify-center gap-2 rounded-full px-5 text-sm font-semibold transition-colors',
                  inAgenda ? 'bg-foreground text-background' : 'bg-primary text-primary-foreground',
                )}
              >
                {inAgenda ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
                {inAgenda ? 'Guardado en tu agenda' : 'Guardar en mi agenda'}
              </button>
              {calendar ? (
                <a
                  href={calendar}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border/80 px-5 text-sm font-semibold hover:bg-muted/60"
                >
                  <CalendarPlus className="h-4 w-4" />
                  Añadir al calendario
                </a>
              ) : null}
              <button
                onClick={handleShare}
                className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-full border border-border/80 px-5 text-sm font-semibold hover:bg-muted/60"
              >
                <Share2 className="h-4 w-4" />
                Compartir
              </button>
            </div>

            {feedback ? <p className="text-sm font-medium text-primary">{feedback}</p> : null}
          </div>
        </div>
      </div>
    </>
  );
}
