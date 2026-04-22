import { getEndOfToday, getSearchBlob, getStartOfToday, isUpcomingEvent, isWithinMadrid, formatEventSchedule, formatLocationLabel, formatRelativeDate, normalizePriceLabel, pickPrimaryDate, pickSecondaryDate, sourceLabel } from './formatters';
import type { MadPlanEvent, MadPlanNews, RawMadPlanEvent, RawMadPlanNews, SourceLink } from './types';

function sanitizeText(value?: string | null): string | undefined {
  if (!value) return undefined;
  return value.replace(/\s+/g, ' ').trim();
}

function dedupe(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.map((value) => sanitizeText(value)).filter(Boolean) as string[]));
}

function normalizeSourceLinks(event: RawMadPlanEvent): SourceLink[] {
  const links = event.metadata?.source_links || [];
  const withPrimary = event.url && !links.some((link) => link.url === event.url)
    ? [{ fuente: event.fuente, url: event.url, kind: event.url_compra ? 'detalle' : 'detalle' }, ...links]
    : links;

  return withPrimary.filter((link) => Boolean(link?.url));
}

export function normalizeEvent(event: RawMadPlanEvent, now = new Date()): MadPlanEvent {
  const primaryDate = pickPrimaryDate(event);
  const secondaryDate = pickSecondaryDate(event);
  const primaryCategory =
    sanitizeText(event.categoria_principal_norm) ||
    sanitizeText(event.categoria_principal) ||
    sanitizeText(event.categorias_normalizadas?.[0]) ||
    sanitizeText(event.categorias?.[0]) ||
    'Plan en Madrid';
  const categoriesList = dedupe([
    ...(event.categorias_normalizadas || []),
    ...(event.categorias || []),
    event.categoria_principal_norm,
    event.categoria_principal,
  ]);
  const searchBlob = getSearchBlob([
    event.titulo,
    event.subtitulo,
    event.resumen,
    event.descripcion,
    event.contenido,
    event.lugar,
    event.direccion,
    categoriesList,
    event.etiquetas || [],
  ]);
  const todayStart = getStartOfToday(now);
  const todayEnd = getEndOfToday(now);
  const weekendEnd = new Date(todayEnd);
  weekendEnd.setDate(weekendEnd.getDate() + (6 - weekendEnd.getDay() + 7) % 7 + 1);
  weekendEnd.setHours(23, 59, 59, 999);
  const weekEnd = new Date(todayEnd);
  weekEnd.setDate(weekEnd.getDate() + 7);
  const monthEnd = new Date(todayEnd);
  monthEnd.setMonth(monthEnd.getMonth() + 1);

  return {
    ...event,
    titulo: sanitizeText(event.titulo) || 'Plan sin título',
    subtitulo: sanitizeText(event.subtitulo),
    resumen: sanitizeText(event.resumen),
    descripcion: sanitizeText(event.descripcion),
    contenido: sanitizeText(event.contenido),
    lugar: sanitizeText(event.lugar),
    direccion: sanitizeText(event.direccion),
    imagen: sanitizeText(event.imagen),
    url: sanitizeText(event.url),
    url_compra: sanitizeText(event.url_compra),
    fuente: event.fuente,
    primaryDate,
    secondaryDate,
    primaryDateLabel: primaryDate ? formatRelativeDate(primaryDate, now) : 'Sin fecha concreta',
    scheduleLabel: formatEventSchedule(event, primaryDate),
    relativeLabel: formatRelativeDate(primaryDate, now),
    priceLabel: normalizePriceLabel(event.precio, event.es_gratis, event.moneda),
    locationLabel: formatLocationLabel(event),
    primaryCategory,
    categoriesList,
    searchBlob,
    isFree: Boolean(event.es_gratis || event.precio === 0 || event.precio === '0'),
    hasCoordinates: isWithinMadrid(event.latitud, event.longitud),
    isToday: Boolean(primaryDate && primaryDate >= todayStart && primaryDate <= todayEnd),
    isThisWeek: Boolean(primaryDate && primaryDate >= todayStart && primaryDate <= weekEnd),
    isThisWeekend: Boolean(primaryDate && primaryDate >= todayStart && primaryDate <= weekendEnd),
    isThisMonth: Boolean(primaryDate && primaryDate >= todayStart && primaryDate <= monthEnd),
    sourceLabel: sourceLabel(event.fuente),
    sourceLinks: normalizeSourceLinks(event),
  };
}

export function normalizeNewsItem(news: RawMadPlanNews): MadPlanNews {
  const publishedDate = pickPrimaryDate({
    id: news.id,
    titulo: news.titulo,
    fuente: news.fuente,
    sort_datetime: news.sort_datetime,
    fecha_inicio: news.publicado_en,
  });

  return {
    ...news,
    titulo: sanitizeText(news.titulo) || 'Noticia sin título',
    subtitulo: sanitizeText(news.subtitulo),
    resumen: sanitizeText(news.resumen),
    descripcion: sanitizeText(news.descripcion),
    contenido: sanitizeText(news.contenido),
    imagen: sanitizeText(news.imagen),
    url: sanitizeText(news.url),
    publishedDate,
    primaryCategory:
      sanitizeText(news.categoria_principal_norm) ||
      sanitizeText(news.categoria_principal) ||
      sanitizeText(news.categorias_normalizadas?.[0]) ||
      sanitizeText(news.categorias?.[0]) ||
      'Actualidad',
    sourceLabel: sourceLabel(news.fuente),
  };
}

export function normalizeEvents(events: RawMadPlanEvent[]): MadPlanEvent[] {
  return events
    .filter((event) => Boolean(event?.id && event?.titulo) && isUpcomingEvent(event))
    .map((event) => normalizeEvent(event))
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

