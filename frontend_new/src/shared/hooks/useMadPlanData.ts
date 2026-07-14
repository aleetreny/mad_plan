import { useEffect, useState } from 'react';
import { normalizeEvents, normalizeNews } from '../../domain/madplan/normalizers';
import type {
  MadPlanEvent,
  MadPlanNews,
  PipelineManifest,
  RawMadPlanEvent,
  RawMadPlanNews,
} from '../../domain/madplan/types';

interface MadPlanState {
  events: MadPlanEvent[];
  news: MadPlanNews[];
  updatedAt: Date | null;
  loading: boolean;
  error: string | null;
}

const INITIAL_STATE: MadPlanState = {
  events: [],
  news: [],
  updatedAt: null,
  loading: true,
  error: null,
};

async function fetchJson<T>(url: string, signal: AbortSignal): Promise<T | null> {
  try {
    const response = await fetch(url, { signal });
    if (!response.ok) return null;
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export function useMadPlanData() {
  const [state, setState] = useState<MadPlanState>(INITIAL_STATE);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      // Relative URLs so the app works both at the domain root and under a
      // subpath like GitHub Pages' /mad_plan/.
      const [rawEvents, rawNews, manifest] = await Promise.all([
        fetchJson<RawMadPlanEvent[]>('outputs/eventos_web.json', controller.signal),
        fetchJson<RawMadPlanNews[]>('outputs/noticias_web.json', controller.signal),
        fetchJson<PipelineManifest>('outputs/pipeline_diario.json', controller.signal),
      ]);

      if (controller.signal.aborted) return;

      const events = Array.isArray(rawEvents) ? normalizeEvents(rawEvents) : [];
      const news = Array.isArray(rawNews) ? normalizeNews(rawNews) : [];
      const updatedAtRaw = manifest?.finished_at;
      const updatedAt = updatedAtRaw ? new Date(updatedAtRaw) : null;

      if (events.length === 0 && news.length === 0) {
        setState({
          events: [],
          news: [],
          updatedAt: null,
          loading: false,
          error: 'No se pudieron cargar los datos. Ejecuta el pipeline (python tools/scrape_all.py) y recarga.',
        });
        return;
      }

      setState({
        events,
        news,
        updatedAt: updatedAt && !Number.isNaN(updatedAt.getTime()) ? updatedAt : null,
        loading: false,
        error: null,
      });
    }

    load();

    return () => {
      controller.abort();
    };
  }, []);

  return state;
}
