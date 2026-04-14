import { X, Calendar, Trash2, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';
import type { MadPlanEvent } from '../types';

function fmtDate(raw?: string | null): string {
  if (!raw) return '';
  try { return new Date(raw).toLocaleDateString('es-ES', { weekday: 'short', day: 'numeric', month: 'short' }); }
  catch { return ''; }
}

interface Props {
  open: boolean;
  onClose: () => void;
  events: MadPlanEvent[];
  onRemove: (id: string) => void;
}

export function AgendaDrawer({ open, onClose, events, onRemove }: Props) {
  if (!open) return null;

  const sorted = [...events].sort((a, b) => {
    const da = a.sort_datetime || a.fecha_inicio || '';
    const db = b.sort_datetime || b.fecha_inicio || '';
    return da.localeCompare(db);
  });

  return (
    <div className="fixed inset-0 z-[100] flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
        className="relative w-full max-w-md bg-background h-full overflow-y-auto shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-background/90 backdrop-blur-md border-b px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-display font-bold">Tu Agenda</h2>
            <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full font-bold">{events.length}</span>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-full hover:bg-muted"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-6">
          {sorted.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Calendar className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="font-medium">Tu agenda está vacía</p>
              <p className="text-sm mt-1">Pulsa + en cualquier evento para añadirlo</p>
            </div>
          ) : (
            <div className="space-y-3">
              {sorted.map(ev => (
                <div key={ev.id} className="flex gap-3 p-3 rounded-xl border bg-card/50 group">
                  <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
                    {ev.imagen ? (
                      <img src={ev.imagen} alt="" className="w-full h-full object-cover" loading="lazy" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center opacity-30"><Calendar className="w-6 h-6" /></div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-bold line-clamp-1">{ev.titulo}</h4>
                    <p className="text-[11px] text-muted-foreground">{fmtDate(ev.sort_datetime || ev.fecha_inicio)}</p>
                    {ev.lugar && <p className="text-[10px] text-muted-foreground line-clamp-1">{ev.lugar}</p>}
                  </div>
                  <div className="flex flex-col gap-1">
                    {ev.url && (
                      <a href={ev.url} target="_blank" rel="noreferrer" className="p-1 rounded hover:bg-muted"><ExternalLink className="w-3.5 h-3.5" /></a>
                    )}
                    <button onClick={() => onRemove(ev.id)} className="p-1 rounded hover:bg-red-100 text-red-500"><Trash2 className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
