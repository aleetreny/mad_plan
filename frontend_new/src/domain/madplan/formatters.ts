import { MADRID_BOUNDS, SOURCE_LABELS } from './constants';
import type { RawMadPlanEvent, TimeOfDay } from './types';

export function parseMadPlanDate(raw?: string | null): Date | null {
  if (!raw) return null;

  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const [year, month, day] = raw.split('-').map(Number);
    return new Date(year, month - 1, day, 12, 0, 0, 0);
  }

  const date = new Date(raw);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function getStartOfToday(now = new Date()): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0, 0);
}

export function getEndOfToday(now = new Date()): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59, 999);
}

export function getCurrentThemeTime(now = new Date()): TimeOfDay {
  const hour = now.getHours();
  if (hour >= 6 && hour < 12) return 'morning';
  if (hour >= 12 && hour < 18) return 'afternoon';
  if (hour >= 18 && hour < 22) return 'evening';
  return 'night';
}

export function sourceLabel(source?: string | null): string {
  return SOURCE_LABELS[source || ''] || source || 'Fuente';
}

export function isWithinMadrid(lat?: number | null, lon?: number | null): boolean {
  if (lat == null || lon == null) return false;
  return (
    lat >= MADRID_BOUNDS.latMin &&
    lat <= MADRID_BOUNDS.latMax &&
    lon >= MADRID_BOUNDS.lonMin &&
    lon <= MADRID_BOUNDS.lonMax
  );
}

export interface EventDates {
  /** Next relevant date for the user: never in the past for ongoing plans. */
  primary: Date | null;
  end: Date | null;
  isOngoing: boolean;
  /** ISO string whose hour matches `primary` (null when there is no real hour). */
  timeSource: string | null;
}

/**
 * Compute the effective dates client-side. The feed's `proxima_fecha` is
 * computed at scrape time and can lag a few days behind, so everything is
 * recalculated here against the real "today".
 */
export function resolveEventDates(event: RawMadPlanEvent, now = new Date()): EventDates {
  const todayStart = getStartOfToday(now);
  const noonToday = new Date(todayStart.getTime() + 12 * 3600000);
  const start = parseMadPlanDate(event.datetime_inicio || event.fecha_inicio);
  const end = parseMadPlanDate(event.fecha_fin);
  const rangeCoversToday = Boolean(start && end && start < todayStart && end >= todayStart);

  const futureSessions = (event.sesiones || [])
    .map((session) => ({
      date: parseMadPlanDate(session.datetime || session.fecha),
      iso: session.datetime || null,
    }))
    .filter((entry): entry is { date: Date; iso: string | null } =>
      Boolean(entry.date && entry.date >= todayStart),
    )
    .sort((a, b) => a.date.getTime() - b.date.getTime());
  const nextSession = futureSessions[0] || null;

  // Multi-date plans: the next real session is what the user can attend.
  if (event.modo_fecha === 'multiple' && nextSession) {
    return { primary: nextSession.date, end, isOngoing: false, timeSource: nextSession.iso };
  }

  // Window plans already open: they are "En curso" today, regardless of the
  // stored window endpoints.
  if (rangeCoversToday) {
    return { primary: noonToday, end, isOngoing: true, timeSource: null };
  }

  if (start && start >= todayStart) {
    return { primary: start, end, isOngoing: false, timeSource: event.datetime_inicio || null };
  }

  if (nextSession) {
    return { primary: nextSession.date, end, isOngoing: false, timeSource: nextSession.iso };
  }

  if (end && end >= todayStart) {
    return { primary: noonToday, end, isOngoing: true, timeSource: null };
  }

  const fallback = parseMadPlanDate(event.proximo_datetime || event.proxima_fecha || event.sort_datetime);
  if (fallback && fallback >= todayStart) {
    const fallbackIso = event.proximo_datetime || null;
    return { primary: fallback, end, isOngoing: false, timeSource: fallbackIso };
  }
  return { primary: null, end, isOngoing: false, timeSource: null };
}

export function formatShortDate(raw?: string | Date | null): string {
  const date = raw instanceof Date ? raw : parseMadPlanDate(raw);
  if (!date) return 'Fecha por confirmar';

  return new Intl.DateTimeFormat('es-ES', {
    day: 'numeric',
    month: 'short',
  }).format(date);
}

export function formatLongDate(raw?: string | Date | null): string {
  const date = raw instanceof Date ? raw : parseMadPlanDate(raw);
  if (!date) return 'Fecha por confirmar';

  return new Intl.DateTimeFormat('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date);
}

export function formatTime(raw?: string | Date | null): string {
  const date = raw instanceof Date ? raw : parseMadPlanDate(raw);
  if (!date) return '';

  const hours = date.getHours();
  const minutes = date.getMinutes();
  if (hours === 0 && minutes === 0) return '';

  return new Intl.DateTimeFormat('es-ES', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

/** Ongoing plans ending further out than this read as "permanent" to users. */
const ONGOING_FAR_FUTURE_MS = 456 * 86400000; // ~15 meses

/** Card-level label: "Hoy · 20:30", "En curso · hasta 24 sep", "vie, 17 jul"… */
export function formatEventSchedule(event: RawMadPlanEvent, dates: EventDates, now = new Date()): string {
  if (dates.isOngoing) {
    const farFuture = dates.end && dates.end.getTime() - now.getTime() > ONGOING_FAR_FUTURE_MS;
    const until = dates.end && !farFuture ? ` · hasta ${formatShortDate(dates.end)}` : '';
    return `En curso${until}`;
  }
  if (!dates.primary) {
    // Undated editorial picks are open plans, not events pending a date.
    return event.modo_fecha === 'sin_fecha' ? 'Cuando quieras' : 'Fecha por confirmar';
  }

  const dayLabel = formatRelativeDay(dates.primary, now);
  const time = formatTime(dates.timeSource);
  return time ? `${dayLabel} · ${time}` : dayLabel;
}

/** "Hoy", "Mañana", "vie, 17 jul" */
export function formatRelativeDay(date: Date | null, now = new Date()): string {
  if (!date) return 'Fecha por confirmar';

  const today = getStartOfToday(now);
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000);

  if (diff === 0) return 'Hoy';
  if (diff === 1) return 'Mañana';

  const sameYear = date.getFullYear() === now.getFullYear();
  return new Intl.DateTimeFormat('es-ES', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: sameYear ? undefined : 'numeric',
  }).format(date);
}

export function normalizePriceLabel(
  price?: number | string | null,
  isFree?: boolean | null,
): string | null {
  if (isFree || price === 0 || price === '0' || price === '0.0') return 'Gratis';
  if (price == null || price === '') return null;

  const numeric = typeof price === 'number' ? price : Number(String(price).replace(',', '.'));
  if (!Number.isNaN(numeric)) {
    if (numeric === 0) return 'Gratis';
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: Number.isInteger(numeric) ? 0 : 2,
    }).format(numeric);
  }

  return String(price);
}

export function formatLocationLabel(event: RawMadPlanEvent): string {
  if (event.lugar && event.direccion && event.lugar !== event.direccion) {
    return `${event.lugar} · ${event.direccion}`;
  }
  return event.lugar || event.direccion || 'Ubicación por confirmar';
}

/** Lowercase + accent-insensitive, so "musica" matches "música". */
export function foldSearchText(text: string): string {
  return text
    .toLocaleLowerCase('es-ES')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
}

export function getSearchBlob(parts: Array<string | null | undefined | string[]>): string {
  return foldSearchText(
    parts
      .flatMap((part) => (Array.isArray(part) ? part : [part]))
      .filter(Boolean)
      .join(' '),
  );
}

/** Distance in km between two coordinates (equirectangular approx, fine at city scale). */
export function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const degToKmLat = 111.32;
  const degToKmLon = 111.32 * Math.cos(((lat1 + lat2) / 2) * (Math.PI / 180));
  const dLat = (lat2 - lat1) * degToKmLat;
  const dLon = (lon2 - lon1) * degToKmLon;
  return Math.sqrt(dLat * dLat + dLon * dLon);
}

/** Grace period before a timed event that already started stops being shown. */
const STARTED_EVENT_GRACE_MS = 3 * 3600000;

function hasRealTime(iso: string): boolean {
  const match = iso.match(/T(\d{2}):(\d{2}):?(\d{2})?/);
  if (!match) return false;
  const stamp = `${match[1]}:${match[2]}`;
  return stamp !== '00:00' && stamp !== '23:59';
}

export function isUpcomingEvent(event: RawMadPlanEvent, now = new Date()): boolean {
  const today = getStartOfToday(now);

  const endIso = event.vigente_hasta || event.fecha_fin;
  const end = parseMadPlanDate(endIso);
  if (end) {
    // A one-off timed plan (concert at 21:00) should disappear a few hours
    // after it starts, not survive until midnight looking bookable.
    if (endIso && hasRealTime(endIso)) {
      return now.getTime() <= end.getTime() + STARTED_EVENT_GRACE_MS;
    }
    return end >= today;
  }

  const start = parseMadPlanDate(event.datetime_inicio || event.fecha_inicio);
  if (start) return start >= today;

  // Undated editorial plans stay visible; the backend already limits how old
  // they can be.
  return true;
}
