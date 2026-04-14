import { useMemo } from 'react';
import type { MadPlanEvent, UserProfile } from '../types';

const VIBE_KEYWORDS: Record<string, string[]> = {
  cultural: ['cultura', 'arte', 'museo', 'exposici', 'teatro', 'cine', 'danza', 'literatura', 'patrimonio', 'historia', 'Arte y Exposiciones', 'Teatro y Danza', 'Cine', 'Lectura y Literatura'],
  fiesta: ['fiesta', 'concierto', 'festival', 'noche', 'dj', 'electr', 'club', 'live', 'musica', 'rock', 'pop', 'Música y Conciertos', 'Vida Nocturna'],
  relax: ['yoga', 'meditaci', 'spa', 'paseo', 'jardin', 'retiro', 'naturaleza', 'bienestar', 'relax', 'Bienestar y Salud', 'Naturaleza y Aire Libre'],
  foodie: ['gastronom', 'tapa', 'comida', 'cocina', 'mercado', 'restaurante', 'wine', 'vino', 'cerveza', 'cata', 'Gastronomía', 'Mercados y Ferias'],
  aventura: ['deporte', 'aventura', 'senderismo', 'escalada', 'bici', 'running', 'trail', 'aire libre', 'outdoor', 'Deportes y Aventura', 'Naturaleza y Aire Libre'],
  familiar: ['familia', 'niño', 'infantil', 'taller', 'educati', 'parque', 'circo', 'magia', 'animacion', 'Familia e Infantil', 'Talleres y Cursos'],
};

export function computeMatchScore(event: MadPlanEvent, profile: UserProfile): number {
  if (!profile.answeredQuiz && !profile.vibe) return 0;
  let score = 0;

  const normCats = event.categorias_normalizadas || [];

  const blob = [
    event.titulo, event.resumen,
    event.categoria_principal_norm,
    ...normCats,
    ...(event.etiquetas || []),
    event.lugar,
  ].filter(Boolean).join(' ').toLowerCase();

  // Vibe matching (0-55 pts) - strengthened
  if (profile.vibe && VIBE_KEYWORDS[profile.vibe]) {
    const kws = VIBE_KEYWORDS[profile.vibe];
    const hits = kws.filter(kw => blob.includes(kw.toLowerCase())).length;
    score += Math.min(55, Math.round((hits / Math.max(kws.length * 0.3, 1)) * 55));
  }

  // Interest matching (0-35 pts) - strengthened
  if (profile.interests.length > 0) {
    const hits = profile.interests.filter(i => blob.includes(i.toLowerCase())).length;
    score += Math.round((hits / profile.interests.length) * 35);
  }

  // Free bonus
  if (event.es_gratis) score += 3;

  // Has image bonus
  if (event.imagen) score += 2;

  // Recency bonus (0-10)
  const sortDt = event.sort_datetime || event.proximo_datetime;
  if (sortDt) {
    const days = (new Date(sortDt).getTime() - Date.now()) / 86400000;
    if (days >= 0 && days <= 3) score += 10;
    else if (days > 3 && days <= 7) score += 5;
  }

  return Math.min(99, Math.max(0, score));
}

export function useMatchScore(events: MadPlanEvent[], profile: UserProfile) {
  return useMemo(() => {
    return events.map(e => ({ event: e, score: computeMatchScore(e, profile) }));
  }, [events, profile]);
}
