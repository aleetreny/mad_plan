import { X, Calendar, MapPin, ExternalLink, Tag, Plus, Check, Share2 } from 'lucide-react';
import { motion } from 'framer-motion';
import type { MadPlanEvent } from '../types';

function fmtFullDate(raw?: string | null): string {
  if (!raw) return 'Fecha por confirmar';
  try {
    return new Date(raw).toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return raw || ''; }
}

interface Props {
  event: MadPlanEvent | null;
  onClose: () => void;
  inAgenda: boolean;
  onToggleAgenda: () => void;
  matchScore?: number;
}

export function EventModal({ event, onClose, inAgenda, onToggleAgenda, matchScore }: Props) {
  if (!event) return null;

  const price = (event.es_gratis || event.precio === 0 || event.precio === '0' || event.precio === 'Gratuito')
    ? 'Gratis'
    : (event.precio != null && event.precio !== '' && event.precio !== '0.0')
      ? (typeof event.precio === 'number' ? `${event.precio}€` : String(event.precio))
      : null;

  return (
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 40 }}
        className="bg-background rounded-t-3xl sm:rounded-3xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {event.imagen && (
          <div className="relative aspect-video overflow-hidden rounded-t-3xl sm:rounded-t-3xl">
            <img src={event.imagen} alt={event.titulo} className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
          </div>
        )}

        <button onClick={onClose} className="absolute top-4 right-4 p-2 rounded-full bg-background/80 backdrop-blur-md hover:bg-muted z-10">
          <X className="w-5 h-5" />
        </button>

        <div className="p-6">
          <div className="flex flex-wrap gap-2 mb-3">
            {(event.categoria_principal_norm || event.categoria_principal) && (
              <span className="px-2 py-1 text-[11px] font-bold rounded-full bg-primary text-primary-foreground">{event.categoria_principal_norm || event.categoria_principal}</span>
            )}
            {price && (
              <span className={`px-2 py-1 text-[11px] font-bold rounded-full ${event.es_gratis ? 'bg-green-500 text-white' : 'bg-secondary text-secondary-foreground'}`}>
                {price}
              </span>
            )}
            {matchScore && matchScore > 0 && (
              <span className="px-2 py-1 text-[11px] font-bold rounded-full bg-accent text-accent-foreground">{matchScore}% Match</span>
            )}
            <span className="px-2 py-1 text-[11px] font-medium rounded-full bg-muted text-muted-foreground">{event.fuente}</span>
          </div>

          <h2 className="text-2xl font-display font-bold mb-2">{event.titulo}</h2>
          {event.subtitulo && <p className="text-muted-foreground mb-3">{event.subtitulo}</p>}

          <div className="flex flex-col gap-2 mb-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-2"><Calendar className="w-4 h-4 text-primary" />{fmtFullDate(event.sort_datetime || event.fecha_inicio)}</span>
            {(event.lugar || event.direccion) && (
              <span className="flex items-center gap-2"><MapPin className="w-4 h-4 text-primary" />{event.lugar}{event.direccion && ` · ${event.direccion}`}</span>
            )}
          </div>

          {(event.resumen || event.descripcion || event.contenido) && (
            <div className="prose prose-sm max-w-none text-foreground/80 mb-4 leading-relaxed">
              <p>{event.contenido || event.descripcion || event.resumen}</p>
            </div>
          )}

          {(event.categorias_normalizadas || event.categorias || []).length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-5">
              {(event.categorias_normalizadas || event.categorias || []).map(c => (
                <span key={c} className="px-2 py-0.5 text-[10px] rounded-full bg-muted text-muted-foreground font-medium flex items-center gap-1">
                  <Tag className="w-2.5 h-2.5" />{c}
                </span>
              ))}
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={onToggleAgenda}
              className={`flex-1 py-3 rounded-full font-bold text-sm flex items-center justify-center gap-2 transition-colors ${
                inAgenda ? 'bg-green-500 text-white' : 'bg-primary text-primary-foreground'
              }`}
            >
              {inAgenda ? <><Check className="w-4 h-4" /> En tu agenda</> : <><Plus className="w-4 h-4" /> Añadir a mi agenda</>}
            </button>
            {event.url && (
              <a href={event.url} target="_blank" rel="noreferrer"
                className="px-6 py-3 rounded-full border font-bold text-sm flex items-center gap-2 hover:bg-muted transition-colors">
                <ExternalLink className="w-4 h-4" /> Ir al evento
              </a>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
