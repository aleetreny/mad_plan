import { ExternalLink } from 'lucide-react';
import type { MadPlanNews } from '../types';

function fmtDate(raw?: string | null): string {
  if (!raw) return '';
  try { return new Date(raw).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' }); }
  catch { return ''; }
}

export function NewsCard({ news }: { news: MadPlanNews }) {
  return (
    <a
      href={news.url || '#'}
      target="_blank"
      rel="noreferrer"
      className="flex gap-3 p-3 rounded-xl bg-card/30 backdrop-blur-sm group cursor-pointer hover:bg-card/50 transition-colors"
    >
      <div className="w-20 h-20 rounded-lg overflow-hidden flex-shrink-0 bg-muted">
        {news.imagen ? (
          <img src={news.imagen} alt={news.titulo} className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" loading="lazy" />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-secondary text-secondary-foreground">
            <span className="text-xs font-bold font-display">NWS</span>
          </div>
        )}
      </div>
      <div className="flex flex-col justify-between py-0.5 flex-1 min-w-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] px-1.5 py-0.5 rounded border border-primary/30 text-primary font-medium">
              {news.categoria_principal || news.fuente}
            </span>
            <span className="text-[10px] text-muted-foreground">{news.fuente}</span>
          </div>
          <h4 className="text-sm font-bold leading-tight line-clamp-2 group-hover:text-primary transition-colors">
            {news.titulo}
          </h4>
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-[10px] text-muted-foreground">{fmtDate(news.publicado_en || news.sort_datetime)}</span>
          <ExternalLink className="w-3 h-3 text-muted-foreground group-hover:text-primary" />
        </div>
      </div>
    </a>
  );
}
