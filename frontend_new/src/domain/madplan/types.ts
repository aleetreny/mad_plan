export type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night';

export type ThemeMode = TimeOfDay | 'auto';

export type VibeMode = 'cultural' | 'fiesta' | 'relax' | 'foodie' | 'aventura' | 'familiar' | null;

export type BudgetPreference = 'free' | 'moderate' | 'flexible' | null;

export type CompanionMode = 'solo' | 'pair' | 'friends' | 'family' | null;

export type DiscoveryView = 'list' | 'map' | 'news';

export type DiscoveryDateFilter = 'all' | 'today' | 'tomorrow' | 'weekend' | 'week' | 'month';

export interface SourceLink {
  fuente?: string | null;
  url: string;
  kind?: string | null;
  precio?: number | string | null;
  es_gratis?: boolean | null;
}

export interface EventSession {
  fecha: string;
  datetime?: string | null;
  tiene_hora: boolean;
}

/** Shape of `outputs/eventos_web.json` records (slim feed). */
export interface RawMadPlanEvent {
  id: string;
  titulo: string;
  subtitulo?: string | null;
  resumen?: string | null;
  descripcion?: string | null;
  imagen?: string | null;
  fuente: string;
  fuentes_relacionadas?: string[] | null;
  categorias_normalizadas?: string[] | null;
  categoria_principal_norm?: string | null;
  url?: string | null;
  url_compra?: string | null;
  lugar?: string | null;
  direccion?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  precio?: number | string | null;
  moneda?: string | null;
  es_gratis?: boolean | null;
  modo_fecha?: string | null;
  estado_temporal?: string | null;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
  datetime_inicio?: string | null;
  proxima_fecha?: string | null;
  proximo_datetime?: string | null;
  sort_datetime?: string | null;
  vigente_hasta?: string | null;
  sesiones?: EventSession[] | null;
  source_links?: SourceLink[] | null;
  valoracion?: number | null;
}

/** Shape of `outputs/noticias_web.json` records (slim feed). */
export interface RawMadPlanNews {
  id: string;
  titulo: string;
  resumen?: string | null;
  imagen?: string | null;
  fuente: string;
  categoria_principal_norm?: string | null;
  url?: string | null;
  publicado_en?: string | null;
  sort_datetime?: string | null;
}

export interface PipelineManifest {
  finished_at?: string | null;
  sources?: Array<{ name: string; status: string; count: number }> | null;
}

export interface MadPlanEvent extends RawMadPlanEvent {
  /** Next relevant date computed client-side (never in the past for ongoing plans). */
  primaryDate: Date | null;
  endDate: Date | null;
  isOngoing: boolean;
  scheduleLabel: string;
  relativeLabel: string;
  priceLabel: string | null;
  locationLabel: string;
  primaryCategory: string;
  categoriesList: string[];
  searchBlob: string;
  isFree: boolean;
  hasCoordinates: boolean;
  isToday: boolean;
  isTomorrow: boolean;
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
