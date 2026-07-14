import {
  formatEventSchedule,
  formatLocationLabel,
  formatRelativeDay,
  getEndOfToday,
  getSearchBlob,
  getStartOfToday,
  isUpcomingEvent,
  isWithinMadrid,
  normalizePriceLabel,
  parseMadPlanDate,
  resolveEventDates,
  sourceLabel,
} from './formatters';
import type { MadPlanEvent, MadPlanNews, RawMadPlanEvent, RawMadPlanNews, SourceLink } from './types';

function sanitizeText(value?: string | null): string | undefined {
  if (!value) return undefined;
  return value.replace(/\s+/g, ' ').trim() || undefined;
}

function isWebUrl(url?: string | null): url is string {
  return Boolean(url && /^https?:\/\//i.test(url));
}

function normalizeSourceLinks(event: RawMadPlanEvent): SourceLink[] {
  const links = (event.source_links || []).filter((link) => isWebUrl(link?.url));
  if (isWebUrl(event.url) && !links.some((link) => link.url === event.url)) {
    links.unshift({ fuente: event.fuente, url: event.url, kind: 'detalle' });
  }
  if (isWebUrl(event.url_compra) && !links.some((link) => link.url === event.url_compra)) {
    links.unshift({ fuente: event.fuente, url: event.url_compra, kind: 'compra' });
  }
  return links;
}

export function normalizeEvent(event: RawMadPlanEvent, now = new Date()): MadPlanEvent {
  const dates = resolveEventDates(event, now);
  const primaryCategory =
    sanitizeText(event.categoria_principal_norm) ||
    sanitizeText(event.categorias_normalizadas?.[0]) ||
    'Ocio y Entretenimiento';
  const categoriesList = event.categorias_normalizadas?.length
    ? Array.from(new Set(event.categorias_normalizadas))
    : [primaryCategory];

  const titulo = sanitizeText(event.titulo) || 'Plan sin título';
  const resumen = sanitizeText(event.resumen);
  const descripcion = sanitizeText(event.descripcion);

  const searchBlob = getSearchBlob([
    titulo,
    event.subtitulo,
    resumen,
    descripcion,
    event.lugar,
    event.direccion,
    categoriesList,
  ]);

  const todayStart = getStartOfToday(now);
  const todayEnd = getEndOfToday(now);
  // Upcoming weekend: next Saturday 00:00 (or today if already Sat/Sun) to Sunday 23:59.
  const weekendEnd = new Date(todayEnd);
  weekendEnd.setDate(weekendEnd.getDate() + ((7 - weekendEnd.getDay()) % 7));
  weekendEnd.setHours(23, 59, 59, 999);
  const weekendStart = new Date(weekendEnd);
  weekendStart.setDate(weekendStart.getDate() - 1);
  weekendStart.setHours(0, 0, 0, 0);
  const effectiveWeekendStart = weekendStart < todayStart ? todayStart : weekendStart;
  const weekEnd = new Date(todayEnd);
  weekEnd.setDate(weekEnd.getDate() + 7);
  const monthEnd = new Date(todayEnd);
  monthEnd.setMonth(monthEnd.getMonth() + 1);

  const primaryDate = dates.primary;
  const isThisWeekend = Boolean(
    (primaryDate && primaryDate >= effectiveWeekendStart && primaryDate <= weekendEnd) ||
    (dates.isOngoing && (!dates.end || dates.end >= effectiveWeekendStart)),
  );

  return {
    ...event,
    titulo,
    subtitulo: sanitizeText(event.subtitulo),
    resumen,
    descripcion,
    lugar: sanitizeText(event.lugar),
    direccion: sanitizeText(event.direccion),
    imagen: isWebUrl(event.imagen) ? sanitizeText(event.imagen) : undefined,
    url: isWebUrl(event.url) ? sanitizeText(event.url) : undefined,
    url_compra: isWebUrl(event.url_compra) ? sanitizeText(event.url_compra) : undefined,
    primaryDate,
    endDate: dates.end,
    isOngoing: dates.isOngoing,
    scheduleLabel: formatEventSchedule(event, dates, now),
    relativeLabel: dates.isOngoing
      ? 'En curso'
      : primaryDate
        ? formatRelativeDay(primaryDate, now)
        : event.modo_fecha === 'sin_fecha'
          ? 'Cuando quieras'
          : 'Fecha por confirmar',
    priceLabel: normalizePriceLabel(event.precio, event.es_gratis),
    locationLabel: formatLocationLabel(event),
    primaryCategory,
    categoriesList,
    searchBlob,
    isFree: Boolean(event.es_gratis || event.precio === 0 || event.precio === '0'),
    hasCoordinates: isWithinMadrid(event.latitud, event.longitud),
    isToday: Boolean(primaryDate && primaryDate >= todayStart && primaryDate <= todayEnd),
    isThisWeek: Boolean(primaryDate && primaryDate >= todayStart && primaryDate <= weekEnd),
    isThisWeekend,
    isThisMonth: Boolean(primaryDate && primaryDate >= todayStart && primaryDate <= monthEnd),
    sourceLabel: sourceLabel(event.fuente),
    sourceLinks: normalizeSourceLinks(event),
  };
}

export function normalizeNewsItem(news: RawMadPlanNews): MadPlanNews {
  return {
    ...news,
    titulo: sanitizeText(news.titulo) || 'Noticia sin título',
    resumen: sanitizeText(news.resumen),
    imagen: isWebUrl(news.imagen) ? sanitizeText(news.imagen) : undefined,
    url: isWebUrl(news.url) ? sanitizeText(news.url) : undefined,
    publishedDate: parseMadPlanDate(news.sort_datetime || news.publicado_en),
    primaryCategory: sanitizeText(news.categoria_principal_norm) || 'Actualidad',
    sourceLabel: sourceLabel(news.fuente),
  };
}

export function normalizeEvents(events: RawMadPlanEvent[], now = new Date()): MadPlanEvent[] {
  return events
    .filter((event) => Boolean(event?.id && event?.titulo) && isUpcomingEvent(event, now))
    .map((event) => normalizeEvent(event, now))
    .sort((left, right) => {
      const leftValue = left.primaryDate?.getTime() || Number.MAX_SAFE_INTEGER;
      const rightValue = right.primaryDate?.getTime() || Number.MAX_SAFE_INTEGER;
      return leftValue - rightValue;
    });
}

export function normalizeNews(news: RawMadPlanNews[]): MadPlanNews[] {
  return news
    .filter((item) => Boolean(item?.id && item?.titulo))
    .map(normalizeNewsItem)
    .sort((left, right) => (right.publishedDate?.getTime() || 0) - (left.publishedDate?.getTime() || 0));
}
