import { ArrowUpRight } from 'lucide-react';
import { formatShortDate } from '../../domain/madplan/formatters';
import type { MadPlanNews } from '../../domain/madplan/types';
import { CategoryCover } from './CategoryCover';

interface NewsCardProps {
  news: MadPlanNews;
  variant?: 'compact' | 'featured';
}

export function NewsCard({ news, variant = 'compact' }: NewsCardProps) {
  if (variant === 'featured') {
    return (
      <a
        href={news.url || '#'}
        target="_blank"
        rel="noreferrer"
        className="group flex flex-col overflow-hidden rounded-3xl border border-border/70 bg-card shadow-[0_10px_36px_rgba(15,10,5,0.07)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_18px_48px_rgba(15,10,5,0.14)]"
      >
        <div className="relative aspect-[16/9] overflow-hidden">
          <CategoryCover
            src={news.imagen}
            alt=""
            category={news.primaryCategory}
            seed={news.id}
            className="transition-transform duration-500 group-hover:scale-[1.04]"
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/45 via-transparent to-transparent" />
          <span className="absolute bottom-3 left-3 rounded-full bg-white/94 px-3 py-1 text-[11px] font-bold text-slate-900">
            {formatShortDate(news.publishedDate)}
          </span>
        </div>
        <div className="flex flex-1 flex-col gap-2 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-primary/85">
            {news.sourceLabel}
          </p>
          <h3 className="line-clamp-3 font-display text-[16px] font-bold leading-snug transition-colors group-hover:text-primary">
            {news.titulo}
          </h3>
          {news.resumen ? (
            <p className="line-clamp-3 text-[13px] leading-5 text-muted-foreground">{news.resumen}</p>
          ) : null}
          <span className="mt-auto inline-flex items-center gap-1 pt-1 text-[13px] font-semibold text-primary">
            Leer en {news.sourceLabel}
            <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
          </span>
        </div>
      </a>
    );
  }

  return (
    <a
      href={news.url || '#'}
      target="_blank"
      rel="noreferrer"
      className="group flex gap-3 rounded-2xl border border-border/60 bg-card/70 p-3 transition-all duration-300 hover:-translate-y-0.5 hover:bg-card"
    >
      <div className="h-[72px] w-[72px] flex-shrink-0 overflow-hidden rounded-xl">
        <CategoryCover
          src={news.imagen}
          alt=""
          category={news.primaryCategory}
          seed={news.id}
          iconSize={24}
          className="transition-transform duration-300 group-hover:scale-105"
        />
      </div>
      <div className="min-w-0 flex-1">
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/80">
          {news.sourceLabel} · {formatShortDate(news.publishedDate)}
        </p>
        <h3 className="line-clamp-2 text-[13px] font-semibold leading-[1.35]">{news.titulo}</h3>
        <span className="mt-1.5 inline-flex items-center gap-1 text-[12px] font-medium text-muted-foreground transition-colors group-hover:text-primary">
          Leer noticia
          <ArrowUpRight className="h-3 w-3" />
        </span>
      </div>
    </a>
  );
}
