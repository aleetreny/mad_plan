import { AnimatePresence, motion } from 'framer-motion';
import { Bookmark, ExternalLink, Trash2, X } from 'lucide-react';
import type { MadPlanEvent } from '../../domain/madplan/types';
import { CategoryCover } from '../../shared/ui/CategoryCover';

interface AgendaDrawerProps {
  open: boolean;
  events: MadPlanEvent[];
  onClose: () => void;
  onRemove: (id: string) => void;
  onOpenEvent: (event: MadPlanEvent) => void;
}

export function AgendaDrawer({ open, events, onClose, onRemove, onOpenEvent }: AgendaDrawerProps) {
  if (!open) return null;

  const sorted = [...events].sort((left, right) => {
    const leftDate = left.primaryDate?.getTime() || Number.MAX_SAFE_INTEGER;
    const rightDate = right.primaryDate?.getTime() || Number.MAX_SAFE_INTEGER;
    return leftDate - rightDate;
  });

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[1100] flex justify-end" onClick={onClose}>
        <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" />
        <motion.aside
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', stiffness: 260, damping: 28 }}
          className="relative h-full w-full max-w-md overflow-y-auto border-l border-border/70 bg-background shadow-[0_24px_80px_rgba(0,0,0,0.32)]"
          onClick={(panelEvent) => panelEvent.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-label="Mi agenda"
        >
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border/70 bg-background/90 px-5 py-4 backdrop-blur-md">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary/12 text-primary">
                <Bookmark className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-display text-xl font-bold">Mi agenda</h2>
                <p className="text-sm text-muted-foreground">
                  {events.length === 1 ? '1 plan guardado' : `${events.length} planes guardados`}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full hover:bg-muted/60"
              aria-label="Cerrar agenda"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-3 p-5">
            {sorted.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-border/80 bg-card/50 p-8 text-center">
                <Bookmark className="mx-auto h-10 w-10 text-muted-foreground/50" />
                <h3 className="mt-4 font-display text-xl font-bold">Aún no hay planes guardados</h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  Toca el marcador de cualquier plan para construir tu ruta por Madrid.
                </p>
              </div>
            ) : (
              sorted.map((event) => (
                <article key={event.id} className="flex gap-3 rounded-2xl border border-border/70 bg-card/75 p-3">
                  <button
                    onClick={() => onOpenEvent(event)}
                    className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-xl"
                    aria-label={`Ver detalle de ${event.titulo}`}
                  >
                    <CategoryCover
                      src={event.imagen}
                      alt=""
                      category={event.primaryCategory}
                      seed={event.id}
                      iconSize={26}
                    />
                  </button>
                  <div className="min-w-0 flex-1">
                    <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-primary/85">
                      {event.scheduleLabel}
                    </p>
                    <button onClick={() => onOpenEvent(event)} className="block text-left">
                      <h3 className="line-clamp-2 text-sm font-semibold leading-5 hover:text-primary">{event.titulo}</h3>
                    </button>
                    <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">{event.lugar || event.direccion || 'Madrid'}</p>
                    <div className="mt-2.5 flex items-center gap-2">
                      {event.url ? (
                        <a
                          href={event.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border/70 hover:bg-muted/60"
                          aria-label="Abrir web del plan"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      ) : null}
                      <button
                        onClick={() => onRemove(event.id)}
                        className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-border/70 text-red-500 hover:bg-red-500/10"
                        aria-label="Quitar de la agenda"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
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
