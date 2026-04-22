import { ExternalLink } from 'lucide-react';
import { formatShortDate } from '../../domain/madplan/formatters';
import type { MadPlanNews } from '../../domain/madplan/types';
import { MediaCover } from './MediaCover';

export function NewsCard({ news }: { news: MadPlanNews }) {
  return (
    <a
      href={news.url || '#'}
      target="_blank"
      rel="noreferrer"
      className="group flex gap-3 rounded-[24px] border border-border/60 bg-card/70 p-3 transition-transform duration-300 hover:-translate-y-0.5 hover:bg-card"
    >
      <div className="h-20 w-20 flex-shrink-0 overflow-hidden rounded-2xl">
        <MediaCover src={news.imagen} alt={news.titulo} className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" fallbackLabel={news.primaryCategory} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/80">
          <span>{news.primaryCategory}</span>
          <span className="text-muted-foreground">· {news.sourceLabel}</span>
        </div>
        <h3 className="line-clamp-2 text-sm font-semibold leading-5">{news.titulo}</h3>
        <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
          <span>{formatShortDate(news.publishedDate)}</span>
          <ExternalLink className="h-3.5 w-3.5 transition-colors group-hover:text-primary" />
        </div>
      </div>
    </a>
  );
}

