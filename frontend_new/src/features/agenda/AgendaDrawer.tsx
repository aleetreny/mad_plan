import { AnimatePresence, motion } from 'framer-motion';
import { CalendarDays, ExternalLink, Trash2, X } from 'lucide-react';
import { formatShortDate } from '../../domain/madplan/formatters';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { MediaCover } from '../../shared/ui/MediaCover';

interface AgendaDrawerProps {
  open: boolean;
  events: MadPlanEvent[];
  onClose: () => void;
  onRemove: (id: string) => void;
}

export function AgendaDrawer({ open, events, onClose, onRemove }: AgendaDrawerProps) {
  if (!open) return null;

  const sorted = [...events].sort((left, right) => {
    const leftDate = left.primaryDate?.getTime() || Number.MAX_SAFE_INTEGER;
    const rightDate = right.primaryDate?.getTime() || Number.MAX_SAFE_INTEGER;
    return leftDate - rightDate;
  });

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[90] flex justify-end" onClick={onClose}>
        <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" />
        <motion.aside
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', stiffness: 260, damping: 28 }}
          className="relative h-full w-full max-w-md overflow-y-auto border-l border-border/70 bg-background shadow-[0_24px_80px_rgba(0,0,0,0.32)]"
          onClick={(panelEvent) => panelEvent.stopPropagation()}
        >
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border/70 bg-background/90 px-5 py-4 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-2xl bg-primary/12 text-primary">
                <CalendarDays className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-display text-xl font-bold">Tu agenda</h2>
                <p className="text-sm text-muted-foreground">{events.length} planes guardados</p>
              </div>
            </div>
            <button onClick={onClose} className="inline-flex h-10 w-10 items-center justify-center rounded-full hover:bg-muted/60" aria-label="Cerrar agenda">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-3 p-5">
            {sorted.length === 0 ? (
              <div className="rounded-[28px] border border-dashed border-border/80 bg-card/50 p-8 text-center">
                <CalendarDays className="mx-auto h-10 w-10 text-muted-foreground/50" />
                <h3 className="mt-4 font-display text-xl font-bold">Tu agenda está vacía</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Guarda planes desde la portada para construir tu ruta ideal por Madrid.
                </p>
              </div>
            ) : (
              sorted.map((event) => (
                <article key={event.id} className="flex gap-3 rounded-[24px] border border-border/70 bg-card/75 p-3">
                  <div className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-2xl">
                    <MediaCover src={event.imagen} alt={event.titulo} className="h-full w-full object-cover" fallbackLabel={event.primaryCategory} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary/85">{formatShortDate(event.primaryDate)}</p>
                    <h3 className="line-clamp-2 text-sm font-semibold leading-5">{event.titulo}</h3>
                    <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">{event.locationLabel}</p>
                    <div className="mt-3 flex items-center gap-2">
                      {event.url ? (
                        <a href={event.url} target="_blank" rel="noreferrer" className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border/70 hover:bg-muted/60" aria-label="Abrir plan guardado">
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      ) : null}
                      <button onClick={() => onRemove(event.id)} className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-border/70 text-red-500 hover:bg-red-50" aria-label="Eliminar de agenda">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>
        </motion.aside>
      </div>
    </AnimatePresence>
  );
}

