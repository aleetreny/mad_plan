import { PAGE_SIZE, ZONES } from './constants';
import { distanceKm, foldSearchText } from './formatters';
import type {
  DiscoveryDateFilter,
  DiscoveryState,
  MadPlanEvent,
  MadPlanNews,
  UserProfile,
  VibeMode,
} from './types';

const VIBE_KEYWORDS: Record<Exclude<VibeMode, null>, string[]> = {
  cultural: ['arte', 'exposición', 'museo', 'cine', 'teatro', 'danza', 'literatura', 'patrimonio'],
  fiesta: ['concierto', 'festival', 'dj', 'noche', 'club', 'música', 'directo'],
  relax: ['bienestar', 'paseo', 'retiro', 'jardín', 'mindfulness', 'spa', 'relax'],
  foodie: ['gastronomía', 'tapa', 'mercado', 'cata', 'vino', 'brunch', 'comida'],
  aventura: ['deporte', 'running', 'trail', 'bici', 'outdoor', 'aventura', 'aire libre'],
  familiar: ['familia', 'infantil', 'niños', 'peques', 'taller', 'cuento', 'marionetas'],
};

const FAMILY_HINTS = ['familia', 'niños', 'infantil', 'peques'];
const FRIENDS_HINTS = ['concierto', 'festival', 'afterwork', 'grupo', 'dj', 'beer', 'brunch'];
const PAIR_HINTS = ['romántico', 'cena', 'pareja', 'cocktail', 'velada'];
const SOLO_HINTS = ['lectura', 'cine', 'museo', 'visita guiada', 'exposición'];

function includesAny(text: string, needles: string[]): number {
  return needles.reduce((hits, needle) => hits + (text.includes(needle) ? 1 : 0), 0);
}

export function scoreEvent(event: MadPlanEvent, profile: UserProfile): number {
  let score = 0;

  if (profile.vibe) {
    const vibeHits = includesAny(event.searchBlob, VIBE_KEYWORDS[profile.vibe]);
    score += Math.min(38, vibeHits * 9);
  }

  if (profile.interests.length > 0) {
    score += Math.min(28, includesAny(event.searchBlob, profile.interests.map((item) => item.toLocaleLowerCase('es-ES'))) * 7);
  }

  if (profile.budget === 'free' && event.isFree) score += 18;
  if (profile.budget === 'moderate') {
    const numericPrice = typeof event.precio === 'number' ? event.precio : null;
    if (event.isFree || (numericPrice !== null && numericPrice <= 25)) score += 12;
  }
  if (profile.budget === 'flexible') score += 4;

  if (profile.companion === 'family') score += includesAny(event.searchBlob, FAMILY_HINTS) * 8;
  if (profile.companion === 'friends') score += includesAny(event.searchBlob, FRIENDS_HINTS) * 7;
  if (profile.companion === 'pair') score += includesAny(event.searchBlob, PAIR_HINTS) * 7;
  if (profile.companion === 'solo') score += includesAny(event.searchBlob, SOLO_HINTS) * 7;

  if (profile.zones.length > 0 && profile.zones.some((zone) => matchesZone(event, zone))) {
    score += 10;
  }

  if (event.isToday) score += 8;
  if (event.isFree) score += 3;
  if (event.imagen) score += 2;

  return Math.max(0, Math.min(99, score));
}

function matchesDateFilter(event: MadPlanEvent, filter: DiscoveryDateFilter): boolean {
  if (filter === 'all') return true;
  if (filter === 'today') return event.isToday || event.isOngoing;
  if (filter === 'weekend') return event.isThisWeekend;
  if (filter === 'week') return event.isThisWeek || event.isOngoing;
  return event.isThisMonth || event.isOngoing;
}

/**
 * Zone match by real distance when the event has coordinates, with a
 * text-match fallback for events that mention the barrio in their venue
 * or address.
 */
export function matchesZone(event: MadPlanEvent, zoneName: string): boolean {
  const zone = ZONES.find((item) => item.name === zoneName);
  if (!zone) return true;

  if (event.hasCoordinates && event.latitud != null && event.longitud != null) {
    return distanceKm(event.latitud, event.longitud, zone.lat, zone.lon) <= zone.radiusKm;
  }

  return event.locationLabel.toLocaleLowerCase('es-ES').includes(zoneName.toLocaleLowerCase('es-ES'));
}

/**
 * Avoid monotonous walls of near-identical plans: caps consecutive cards of
 * the same category at two, deferring the excess a little further down.
 */
function diversifyByCategory<T extends { event: MadPlanEvent }>(entries: T[]): T[] {
  const result: T[] = [];
  const pending: T[] = [];

  const lastTwoAre = (category: string) =>
    result.length >= 2 &&
    result[result.length - 1].event.primaryCategory === category &&
    result[result.length - 2].event.primaryCategory === category;

  const drainPending = () => {
    for (let index = 0; index < pending.length; index += 1) {
      if (!lastTwoAre(pending[index].event.primaryCategory)) {
        result.push(pending.splice(index, 1)[0]);
        index = -1; // rescan from the start after each successful insert
      }
    }
  };

  for (const entry of entries) {
    if (lastTwoAre(entry.event.primaryCategory)) {
      pending.push(entry);
    } else {
      result.push(entry);
      drainPending();
    }
  }
  return result.concat(pending);
}

export function filterAndRankEvents(events: MadPlanEvent[], state: DiscoveryState, profile: UserProfile) {
  // Word-level AND matching: "jazz retiro" finds plans mentioning both
  // words anywhere, in any order.
  const queryTokens = foldSearchText(state.query.trim()).split(/\s+/).filter(Boolean);
  const personalized = profile.answeredQuiz || Boolean(profile.vibe);

  const ranked = events
    .filter((event) => {
      if (state.source && event.fuente !== state.source && !(event.fuentes_relacionadas || []).includes(state.source)) return false;
      if (state.category && !event.categoriesList.includes(state.category)) return false;
      if (state.freeOnly && !event.isFree) return false;
      if (state.zone && !matchesZone(event, state.zone)) return false;
      if (queryTokens.length > 0 && !queryTokens.every((token) => event.searchBlob.includes(token))) return false;
      return matchesDateFilter(event, state.dateFilter);
    })
    .map((event) => ({ event, score: scoreEvent(event, profile) }))
    .sort((left, right) => {
      if (personalized && right.score !== left.score) return right.score - left.score;
      const leftDay = left.event.primaryDate ? Math.floor(left.event.primaryDate.getTime() / 86400000) : Number.MAX_SAFE_INTEGER;
      const rightDay = right.event.primaryDate ? Math.floor(right.event.primaryDate.getTime() / 86400000) : Number.MAX_SAFE_INTEGER;
      if (leftDay !== rightDay) return leftDay - rightDay;
      // Same day: one-off events with a real date beat long-running "en curso"
      // exhibitions, so the front page feels alive instead of static.
      if (left.event.isOngoing !== right.event.isOngoing) return left.event.isOngoing ? 1 : -1;
      const leftTime = left.event.primaryDate?.getTime() || 0;
      const rightTime = right.event.primaryDate?.getTime() || 0;
      if (leftTime !== rightTime) return leftTime - rightTime;
      return left.event.titulo.localeCompare(right.event.titulo, 'es-ES');
    });

  // Only the neutral browse view gets diversified; explicit filters or a
  // personal profile mean the user already chose what they want to see.
  if (!personalized && !state.category && queryTokens.length === 0) {
    return diversifyByCategory(ranked);
  }
  return ranked;
}

export function deriveFacetOptions(events: MadPlanEvent[]) {
  const categories = new Map<string, number>();
  const sources = new Map<string, number>();

  events.forEach((event) => {
    sources.set(event.fuente, (sources.get(event.fuente) || 0) + 1);
    event.categoriesList.forEach((category) => {
      categories.set(category, (categories.get(category) || 0) + 1);
    });
  });

  return {
    categories: Array.from(categories.entries())
      .sort((left, right) => right[1] - left[1])
      .map(([category]) => category),
    sources: Array.from(sources.entries())
      .sort((left, right) => right[1] - left[1])
      .map(([source]) => source),
  };
}

export function deriveFeaturedEvents(events: MadPlanEvent[], profile: UserProfile) {
  if (!profile.answeredQuiz && !profile.vibe) return [];
  return events
    // Featured picks must be concrete, dated plans — undated editorial
    // guides score high on keywords but are not something you can attend.
    .filter((event) => event.modo_fecha !== 'sin_fecha' && event.primaryDate)
    .map((event) => ({ event, score: scoreEvent(event, profile) }))
    .filter((entry) => entry.score > 20)
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return (left.event.primaryDate?.getTime() || 0) - (right.event.primaryDate?.getTime() || 0);
    })
    .slice(0, 6);
}

export interface CityStats {
  total: number;
  freeToday: number;
  today: number;
  withCoordinates: number;
  news: number;
}

export function deriveCityStats(events: MadPlanEvent[], news: MadPlanNews[]): CityStats {
  return {
    total: events.length,
    freeToday: events.filter((event) => (event.isToday || event.isOngoing) && event.isFree).length,
    today: events.filter((event) => event.isToday || event.isOngoing).length,
    withCoordinates: events.filter((event) => event.hasCoordinates).length,
    news: news.length,
  };
}

export function deriveVisibleEvents(scoredEvents: Array<{ event: MadPlanEvent; score: number }>, showCount: number) {
  return scoredEvents.slice(0, showCount);
}

export function hasActiveFilters(state: DiscoveryState): boolean {
  return Boolean(state.query || state.source || state.category || state.zone || state.freeOnly || state.dateFilter !== 'all');
}

export function nextShowCount(current: number): number {
  return current + PAGE_SIZE;
}
