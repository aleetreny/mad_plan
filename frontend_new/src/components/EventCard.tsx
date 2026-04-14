import { motion } from 'framer-motion';
import { Calendar, MapPin, Clock, Star, Plus, Check, ExternalLink } from 'lucide-react';
import type { MadPlanEvent } from '../types';
import { cn } from '../lib/utils';

function fmtDate(ev: MadPlanEvent): string {
  const raw = ev.sort_datetime || ev.proximo_datetime || ev.datetime_inicio || ev.fecha_inicio;
  if (!raw) return 'Fecha por confirmar';
  try {
    const d = new Date(raw);
    return d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }) +
      (ev.sort_datetime && new Date(ev.sort_datetime).getHours() > 0
        ? ' · ' + d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
        : '');
  } catch { return raw; }
}

function fmtPrice(ev: MadPlanEvent): string {
  if (ev.es_gratis || ev.precio === 0 || ev.precio === '0') return 'Gratis';
  if (ev.precio == null) return '';
  return typeof ev.precio === 'number' ? `${ev.precio}€` : String(ev.precio);
}

interface Props {
  event: MadPlanEvent;
  matchScore?: number;
  inAgenda?: boolean;
  onToggleAgenda?: () => void;
  onOpen?: () => void;
}

export function EventCard({ event, matchScore, inAgenda, onToggleAgenda, onOpen }: Props) {
  const price = fmtPrice(event);
  const dateStr = fmtDate(event);

  return (
    <motion.div
      whileHover={{ y: -4 }}
      transition={{ duration: 0.2 }}
      className="overflow-hidden rounded-2xl border shadow-md bg-card/50 backdrop-blur-sm group cursor-pointer"
      onClick={onOpen}
    >
      <div className="relative aspect-[16/10] overflow-hidden bg-gradient-to-br from-muted to-border">
        {event.imagen ? (
          <img src={event.imagen} alt={event.titulo} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" loading="lazy" />
        ) : (
          <div className="w-full h-full flex items-center justify-center opacity-20">
            <Calendar className="w-16 h-16" />
          </div>
        )}
        <div className="absolute top-3 left-3 flex gap-2">
          <span className="px-2 py-1 text-[10px] font-bold rounded-md bg-background/80 backdrop-blur-md text-foreground capitalize">
            {event.categoria_principal_norm || event.categoria_principal || event.categorias_normalizadas?.[0] || event.categorias?.[0] || event.fuente}
          </span>
        </div>
        <div className="absolute top-3 right-3 flex flex-col gap-1.5 items-end">
          {price && (
            <span className={cn("px-2 py-1 text-[10px] font-bold rounded-md border-none",
              event.es_gratis ? "bg-green-500 text-white" : "bg-primary text-primary-foreground"
            )}>
              {price}
            </span>
          )}
          {matchScore && matchScore > 0 && (
            <span className="px-2 py-1 text-[10px] font-bold rounded-md bg-accent text-accent-foreground">
              {matchScore}% Match
            </span>
          )}
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
            <Calendar className="w-3 h-3" />
            {dateStr}
          </div>
          <span className="text-[10px] text-muted-foreground font-medium">{event.fuente}</span>
        </div>
        <h3 className="text-base font-display font-bold mb-1.5 line-clamp-2 group-hover:text-primary transition-colors leading-tight">
          {event.titulo}
        </h3>
        {(event.resumen || event.descripcion) && (
          <p className="text-xs text-muted-foreground line-clamp-2 mb-3 leading-relaxed">
            {event.resumen || event.descripcion}
          </p>
        )}
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1 text-[11px] text-muted-foreground">
            {(event.lugar || event.direccion) && (
              <span className="flex items-center gap-1.5">
                <MapPin className="w-3 h-3 flex-shrink-0" />
                <span className="line-clamp-1">{event.lugar || event.direccion}</span>
              </span>
            )}
          </div>
          <div className="flex gap-1.5">
            {event.url && (
              <a href={event.url} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}
                className="p-1.5 rounded-full hover:bg-muted transition-colors" title="Abrir enlace">
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
            <button
              onClick={e => { e.stopPropagation(); onToggleAgenda?.(); }}
              className={cn(
                "p-1.5 rounded-full transition-colors",
                inAgenda ? "bg-primary text-primary-foreground" : "hover:bg-muted"
              )}
              title={inAgenda ? "Quitar de agenda" : "Añadir a agenda"}
            >
              {inAgenda ? <Check className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
