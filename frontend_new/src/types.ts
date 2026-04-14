export interface MadPlanEvent {
  id: string;
  titulo: string;
  subtitulo?: string;
  resumen?: string;
  descripcion?: string;
  contenido?: string;
  imagen?: string | null;
  datetime_inicio?: string | null;
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
  moneda?: string;
  es_gratis?: boolean;
  fuente: string;
  fuente_id?: string;
  categorias?: string[];
  categoria_principal?: string;
  categorias_normalizadas?: string[];
  categoria_principal_norm?: string;
  etiquetas?: string[];
  url?: string;
  url_compra?: string | null;
  tipo?: string;
  estado_temporal?: string;
  sesiones?: { fecha: string; datetime?: string | null; tiene_hora: boolean }[];
  fechas_disponibles?: string[];
}

export interface MadPlanNews {
  id: string;
  titulo: string;
  subtitulo?: string;
  resumen?: string;
  descripcion?: string;
  imagen?: string | null;
  fuente: string;
  categoria_principal?: string;
  categorias?: string[];
  publicado_en?: string | null;
  sort_datetime?: string | null;
  url?: string;
  enlace?: string;
}

export type TimeOfDay = 'morning' | 'afternoon' | 'evening' | 'night';

export type VibeMode = 'cultural' | 'fiesta' | 'relax' | 'foodie' | 'aventura' | 'familiar' | null;

export interface UserProfile {
  interests: string[];
  answeredQuiz: boolean;
  agenda: string[]; // event ids
  vibe: VibeMode;
}
