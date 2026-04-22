import type {
  BudgetPreference,
  CompanionMode,
  ThemeMode,
  TimeOfDay,
  VibeMode,
} from './types';

export const PAGE_SIZE = 12;

export const MADRID_CENTER: [number, number] = [40.4168, -3.7038];

export const MADRID_BOUNDS = {
  latMin: 40.25,
  latMax: 40.6,
  lonMin: -3.92,
  lonMax: -3.48,
};

export const SOURCE_LABELS: Record<string, string> = {
  datos_madrid: 'Datos Madrid',
  esmadrid: 'esMadrid',
  fever: 'Fever',
  eventbrite: 'Eventbrite',
  wegow: 'Wegow',
  ticketmaster: 'Ticketmaster',
  madrid_secreto: 'Madrid Secreto',
  timeout: 'Time Out Madrid',
  matadero: 'Matadero',
  teatros_canal: 'Teatros del Canal',
  circulo_bellas_artes: 'Círculo de Bellas Artes',
  ifema_madrid: 'IFEMA Madrid',
  casa_mexico: 'Casa de México',
  espacio_fundacion_telefonica: 'Fundación Telefónica',
  museo_reina_sofia: 'Museo Reina Sofía',
  biblioteca_nacional: 'Biblioteca Nacional',
  fundacion_canal: 'Fundación Canal',
  fundacion_mapfre: 'Fundación MAPFRE',
  sala_el_sol: 'Sala El Sol',
  gacetin_madrid: 'Gacetín Madrid',
  rockthesport: 'RockTheSport',
  meetup: 'Meetup',
};

export const ZONES = [
  'Centro',
  'Malasaña',
  'Chueca',
  'Lavapiés',
  'Chamberí',
  'Salamanca',
  'Retiro',
  'La Latina',
  'Arganzuela',
  'Usera',
  'Moncloa',
  'Tetuán',
  'Chamartín',
  'Carabanchel',
  'Vallecas',
] as const;

export const VIBE_META: Record<Exclude<VibeMode, null>, { label: string; emoji: string; description: string }> = {
  cultural: {
    label: 'Cultural',
    emoji: '🎨',
    description: 'Museos, exposiciones, cine y escena.',
  },
  fiesta: {
    label: 'Fiesta',
    emoji: '🎶',
    description: 'Conciertos, clubbing y noches con energía.',
  },
  relax: {
    label: 'Relax',
    emoji: '🌿',
    description: 'Paseos, bienestar y planes sin fricción.',
  },
  foodie: {
    label: 'Foodie',
    emoji: '🍷',
    description: 'Mercados, catas y sitios para saborear Madrid.',
  },
  aventura: {
    label: 'Aventura',
    emoji: '🏃',
    description: 'Outdoor, deporte y planes activos.',
  },
  familiar: {
    label: 'Familiar',
    emoji: '👨‍👩‍👧',
    description: 'Actividades cómodas para ir con peques.',
  },
};

export const THEME_META: Record<TimeOfDay, { label: string; accent: string }> = {
  morning: { label: 'Mañana', accent: 'Amanecer castizo' },
  afternoon: { label: 'Tarde', accent: 'Madrid en verde' },
  evening: { label: 'Atardecer', accent: 'Terracota urbana' },
  night: { label: 'Noche', accent: 'Noche de Gran Vía' },
};

export const THEME_MODES: ThemeMode[] = ['auto', 'morning', 'afternoon', 'evening', 'night'];

export const BUDGET_LABELS: Record<Exclude<BudgetPreference, null>, string> = {
  free: 'Solo gratis',
  moderate: 'Hasta 25 €',
  flexible: 'Sin límite',
};

export const COMPANION_LABELS: Record<Exclude<CompanionMode, null>, string> = {
  solo: 'Voy solo/a',
  pair: 'En pareja',
  friends: 'Con amigos',
  family: 'En familia',
};

