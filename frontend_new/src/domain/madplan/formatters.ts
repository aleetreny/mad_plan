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

export function pickPrimaryDate(event: RawMadPlanEvent): Date | null {
  return (
    parseMadPlanDate(event.sort_datetime) ||
    parseMadPlanDate(event.proximo_datetime) ||
    parseMadPlanDate(event.datetime_inicio) ||
    parseMadPlanDate(event.fecha_inicio) ||
    parseMadPlanDate(event.fecha_fin)
  );
}

export function pickSecondaryDate(event: RawMadPlanEvent): Date | null {
  return parseMadPlanDate(event.fecha_fin) || parseMadPlanDate(event.datetime_fin);
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

export function formatEventSchedule(event: RawMadPlanEvent, primaryDate: Date | null): string {
  if (!primaryDate) return 'Fecha por confirmar';

  const time = formatTime(event.sort_datetime || event.proximo_datetime || event.datetime_inicio);
  const dateLabel = formatShortDate(primaryDate);
  return time ? `${dateLabel} · ${time}` : dateLabel;
}

export function formatRelativeDate(date: Date | null, now = new Date()): string {
  if (!date) return 'Sin fecha concreta';

  const today = getStartOfToday(now);
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000);

  if (diff === 0) return 'Hoy';
  if (diff === 1) return 'Mañana';
  if (diff > 1 && diff < 7) {
    return `En ${diff} días`;
  }

  return formatLongDate(date);
}

export function normalizePriceLabel(price?: number | string | null, isFree?: boolean | null, currency?: string | null): string {
  if (isFree || price === 0 || price === '0' || price === '0.0') return 'Gratis';
  if (price == null || price === '') return 'Precio pendiente';
  if (typeof price === 'number') {
    return new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: currency || 'EUR',
      maximumFractionDigits: Number.isInteger(price) ? 0 : 2,
    }).format(price);
  }

  return String(price);
}

export function formatLocationLabel(event: RawMadPlanEvent): string {
  if (event.lugar && event.direccion) return `${event.lugar} · ${event.direccion}`;
  return event.lugar || event.direccion || 'Ubicación por confirmar';
}

export function getSearchBlob(parts: Array<string | null | undefined | string[]>): string {
  return parts
    .flatMap((part) => Array.isArray(part) ? part : [part])
    .filter(Boolean)
    .join(' ')
    .toLocaleLowerCase('es-ES');
}

export function isUpcomingEvent(event: RawMadPlanEvent, now = new Date()): boolean {
  const today = getStartOfToday(now);
  const end = pickSecondaryDate(event);
  if (end) {
    return end >= today;
  }

  const start = pickPrimaryDate(event);
  return start ? start >= today : true;
}

