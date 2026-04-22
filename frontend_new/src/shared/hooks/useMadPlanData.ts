import { useEffect, useState } from 'react';
import { normalizeEvents, normalizeNews } from '../../domain/madplan/normalizers';
import type { MadPlanEvent, MadPlanNews, RawMadPlanEvent, RawMadPlanNews } from '../../domain/madplan/types';

interface MadPlanState {
  events: MadPlanEvent[];
  news: MadPlanNews[];
  loading: boolean;
  error: string | null;
}

const INITIAL_STATE: MadPlanState = {
  events: [],
  news: [],
  loading: true,
  error: null,
};

export function useMadPlanData() {
  const [state, setState] = useState<MadPlanState>(INITIAL_STATE);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      try {
        const [eventsResponse, newsResponse] = await Promise.allSettled([
          fetch('/outputs/eventos_madrid_all.json', { signal: controller.signal }),
          fetch('/outputs/noticias_madrid_all.json', { signal: controller.signal }),
        ]);

        const events =
          eventsResponse.status === 'fulfilled' && eventsResponse.value.ok
            ? normalizeEvents((await eventsResponse.value.json()) as RawMadPlanEvent[])
            : [];
        const news =
          newsResponse.status === 'fulfilled' && newsResponse.value.ok
            ? normalizeNews((await newsResponse.value.json()) as RawMadPlanNews[])
            : [];

        if (events.length === 0 && news.length === 0) {
          throw new Error('No se pudieron cargar los datos de planes ni de noticias.');
        }

        setState({
          events,
          news,
          loading: false,
          error: null,
        });
      } catch (error) {
        if (controller.signal.aborted) return;
        const message = error instanceof Error ? error.message : 'No se pudieron cargar los datos de MadPlan.';
        setState({
          events: [],
          news: [],
          loading: false,
          error: message,
        });
      }
    }

    load();

    return () => {
      controller.abort();
    };
  }, []);

  return state;
}

