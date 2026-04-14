import { useState, useEffect } from 'react';
import type { MadPlanEvent, MadPlanNews } from '../types';

function isFutureOrToday(event: MadPlanEvent): boolean {
  const raw = event.sort_datetime || event.proximo_datetime || event.fecha_fin || event.fecha_inicio;
  if (!raw) return true; // undated events pass through
  try {
    const d = new Date(raw);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return d >= today;
  } catch {
    return true;
  }
}

export function useMadPlanData() {
  const [events, setEvents] = useState<MadPlanEvent[]>([]);
  const [news, setNews] = useState<MadPlanNews[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [evR, nwR] = await Promise.all([
          fetch('/outputs/eventos_madrid_all.json'),
          fetch('/outputs/noticias_madrid_all.json'),
        ]);
        if (!evR.ok && !nwR.ok) throw new Error('No se encontraron datos');
        const evData: MadPlanEvent[] = evR.ok ? await evR.json() : [];
        const nwData: MadPlanNews[] = nwR.ok ? await nwR.json() : [];
        setEvents(evData.filter(e => e.titulo && isFutureOrToday(e)));
        setNews(nwData.filter(n => n.titulo));
      } catch (e: any) {
        setError(e.message || 'Error al cargar datos');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return { events, news, loading, error };
}
