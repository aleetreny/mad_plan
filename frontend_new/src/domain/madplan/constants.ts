import type { LucideIcon } from 'lucide-react';
import {
  Baby,
  BookOpen,
  Clapperboard,
  Drama,
  FlaskConical,
  Footprints,
  GraduationCap,
  HeartHandshake,
  HeartPulse,
  Landmark,
  MicVocal,
  MoonStar,
  Music,
  Palette,
  PartyPopper,
  Store,
  TreePine,
  Trophy,
  UtensilsCrossed,
} from 'lucide-react';
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

export interface CategoryMeta {
  icon: LucideIcon;
  short: string;
  /** Gradient stops for the generated cover (dark editorial tones). */
  from: string;
  to: string;
}

/**
 * Visual identity for the 18 canonical categories produced by
 * tools/normalize_categories.py. Every plan without a real photo gets a
 * deterministic cover built from this palette, so the grid stays uniform.
 */
export const CATEGORY_META: Record<string, CategoryMeta> = {
  'Música y Conciertos': { icon: Music, short: 'Música', from: '#7c3aed', to: '#312e81' },
  'Arte y Exposiciones': { icon: Palette, short: 'Arte', from: '#e11d48', to: '#7f1d1d' },
  'Teatro y Danza': { icon: Drama, short: 'Teatro', from: '#c026d3', to: '#581c87' },
  'Cine': { icon: Clapperboard, short: 'Cine', from: '#0f766e', to: '#134e4a' },
  'Gastronomía': { icon: UtensilsCrossed, short: 'Gastro', from: '#ea580c', to: '#7c2d12' },
  'Deportes y Aventura': { icon: Trophy, short: 'Deporte', from: '#16a34a', to: '#14532d' },
  'Vida Nocturna': { icon: MoonStar, short: 'Noche', from: '#4f46e5', to: '#1e1b4b' },
  'Familia e Infantil': { icon: Baby, short: 'Familia', from: '#f59e0b', to: '#92400e' },
  'Talleres y Cursos': { icon: GraduationCap, short: 'Talleres', from: '#0891b2', to: '#164e63' },
  'Conferencias y Charlas': { icon: MicVocal, short: 'Charlas', from: '#64748b', to: '#1e293b' },
  'Naturaleza y Aire Libre': { icon: TreePine, short: 'Aire libre', from: '#65a30d', to: '#365314' },
  'Bienestar y Salud': { icon: HeartPulse, short: 'Bienestar', from: '#0d9488', to: '#115e59' },
  'Visitas y Rutas': { icon: Footprints, short: 'Rutas', from: '#b45309', to: '#78350f' },
  'Ciencia y Tecnología': { icon: FlaskConical, short: 'Ciencia', from: '#2563eb', to: '#1e3a8a' },
  'Mercados y Ferias': { icon: Store, short: 'Mercados', from: '#d97706', to: '#713f12' },
  'Comunidad y Social': { icon: HeartHandshake, short: 'Comunidad', from: '#db2777', to: '#831843' },
  'Lectura y Literatura': { icon: BookOpen, short: 'Lectura', from: '#9333ea', to: '#4c1d95' },
  'Ocio y Entretenimiento': { icon: PartyPopper, short: 'Ocio', from: '#dc2626', to: '#7f1d1d' },
};

export const FALLBACK_CATEGORY_META: CategoryMeta = {
  icon: Landmark,
  short: 'Madrid',
  from: '#c96f2d',
  to: '#78350f',
};

export function categoryMeta(category?: string | null): CategoryMeta {
  return (category && CATEGORY_META[category]) || FALLBACK_CATEGORY_META;
}

export interface ZoneMeta {
  name: string;
  lat: number;
  lon: number;
  radiusKm: number;
}

/** Approximate barrio/distrito centers used for the geo-based zone filter. */
export const ZONES: ZoneMeta[] = [
  { name: 'Centro', lat: 40.4155, lon: -3.7074, radiusKm: 1.4 },
  { name: 'Malasaña', lat: 40.4265, lon: -3.7038, radiusKm: 0.9 },
  { name: 'Chueca', lat: 40.4223, lon: -3.6973, radiusKm: 0.8 },
  { name: 'Lavapiés', lat: 40.4087, lon: -3.7003, radiusKm: 0.9 },
  { name: 'La Latina', lat: 40.4103, lon: -3.7133, radiusKm: 0.9 },
  { name: 'Chamberí', lat: 40.434, lon: -3.7043, radiusKm: 1.6 },
  { name: 'Salamanca', lat: 40.43, lon: -3.678, radiusKm: 1.7 },
  { name: 'Retiro', lat: 40.411, lon: -3.676, radiusKm: 1.7 },
  { name: 'Arganzuela', lat: 40.398, lon: -3.695, radiusKm: 1.9 },
  { name: 'Moncloa', lat: 40.435, lon: -3.719, radiusKm: 1.9 },
  { name: 'Chamartín', lat: 40.462, lon: -3.677, radiusKm: 2.1 },
  { name: 'Tetuán', lat: 40.46, lon: -3.698, radiusKm: 1.9 },
  { name: 'Usera', lat: 40.381, lon: -3.706, radiusKm: 1.9 },
  { name: 'Carabanchel', lat: 40.383, lon: -3.744, radiusKm: 2.3 },
  { name: 'Vallecas', lat: 40.398, lon: -3.621, radiusKm: 2.6 },
];

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
    description: 'Paseos, bienestar y planes sin prisas.',
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
