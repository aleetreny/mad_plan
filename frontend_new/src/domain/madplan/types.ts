export type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night';

export type ThemeMode = TimeOfDay | 'auto';

export type VibeMode = 'cultural' | 'fiesta' | 'relax' | 'foodie' | 'aventura' | 'familiar' | null;

export type BudgetPreference = 'free' | 'moderate' | 'flexible' | null;

export type CompanionMode = 'solo' | 'pair' | 'friends' | 'family' | null;

export type DiscoveryView = 'list' | 'map';

export type DiscoveryDateFilter = 'all' | 'today' | 'weekend' | 'week' | 'month';

export interface SourceLink {
  fuente: string;
  url: string;
  kind?: string | null;
  precio?: number | string | null;
  moneda?: string | null;
  es_gratis?: boolean | null;
}

export interface RawMadPlanEvent {
  id: string;
  titulo: string;
  subtitulo?: string | null;
  resumen?: string | null;
  descripcion?: string | null;
  contenido?: string | null;
  imagen?: string | null;
  datetime_inicio?: string | null;
  datetime_fin?: string | null;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
  sort_datetime?: string | null;
  proxima_fecha?: string | null;
  proximo_datetime?: string | null;
  lugar?: string | null;
  direccion?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  precio?: number | string | null;
  moneda?: string | null;
  es_gratis?: boolean | null;
  fuente: string;
  fuente_id?: string | null;
  categorias?: string[] | null;
  categoria_principal?: string | null;
  categorias_normalizadas?: string[] | null;
  categoria_principal_norm?: string | null;
  etiquetas?: string[] | null;
  url?: string | null;
  url_compra?: string | null;
  tipo?: string | null;
  estado_temporal?: string | null;
  sesiones?: { fecha: string; datetime?: string | null; tiene_hora: boolean }[] | null;
  fechas_disponibles?: string[] | null;
  metadata?: {
    source_links?: SourceLink[];
    [key: string]: unknown;
  } | null;
}

export interface RawMadPlanNews {
  id: string;
  titulo: string;
  subtitulo?: string | null;
  resumen?: string | null;
  descripcion?: string | null;
  contenido?: string | null;
  imagen?: string | null;
  fuente: string;
  categoria_principal?: string | null;
  categorias?: string[] | null;
  categorias_normalizadas?: string[] | null;
  categoria_principal_norm?: string | null;
  publicado_en?: string | null;
  actualizado_en?: string | null;
  sort_datetime?: string | null;
  url?: string | null;
}

export interface MadPlanEvent extends RawMadPlanEvent {
  primaryDate: Date | null;
  secondaryDate: Date | null;
  primaryDateLabel: string;
  scheduleLabel: string;
  relativeLabel: string;
  priceLabel: string;
  locationLabel: string;
  primaryCategory: string;
  categoriesList: string[];
  searchBlob: string;
  isFree: boolean;
  hasCoordinates: boolean;
  isToday: boolean;
  isThisWeek: boolean;
  isThisWeekend: boolean;
  isThisMonth: boolean;
  sourceLabel: string;
  sourceLinks: SourceLink[];
}

export interface MadPlanNews extends RawMadPlanNews {
  publishedDate: Date | null;
  primaryCategory: string;
  sourceLabel: string;
}

export interface UserProfile {
  interests: string[];
  answeredQuiz: boolean;
  agenda: string[];
  vibe: VibeMode;
  budget: BudgetPreference;
  companion: CompanionMode;
  zones: string[];
}

export interface DiscoveryState {
  query: string;
  source: string | null;
  category: string | null;
  dateFilter: DiscoveryDateFilter;
  freeOnly: boolean;
  zone: string | null;
  view: DiscoveryView;
  showCount: number;
}

