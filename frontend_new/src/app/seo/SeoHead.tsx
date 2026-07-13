import { useEffect } from 'react';
import type { MadPlanEvent, MadPlanNews } from '../../domain/madplan/types';

interface SeoHeadProps {
  events: MadPlanEvent[];
  news: MadPlanNews[];
}

function ensureMeta(selector: string, create: () => HTMLElement): HTMLElement {
  let element = document.head.querySelector(selector) as HTMLElement | null;
  if (!element) {
    element = create();
    document.head.appendChild(element);
  }

  return element;
}

export function SeoHead({ events, news }: SeoHeadProps) {
  useEffect(() => {
    const freeToday = events.filter((event) => (event.isToday || event.isOngoing) && event.isFree).length;
    const title = events.length > 0
      ? `MadPlan · ${events.length.toLocaleString('es-ES')} planes en Madrid`
      : 'MadPlan · Planes y agenda de Madrid';
    const description = `La agenda de Madrid en un solo sitio: conciertos, expos, mercados y rutas con mapa y filtros útiles. ${freeToday} planes gratis hoy.`;

    document.title = title;

    const descriptionMeta = ensureMeta('meta[name="description"]', () => {
      const meta = document.createElement('meta');
      meta.setAttribute('name', 'description');
      return meta;
    });
    descriptionMeta.setAttribute('content', description);

    const canonical = ensureMeta('link[rel="canonical"]', () => {
      const link = document.createElement('link');
      link.setAttribute('rel', 'canonical');
      return link;
    });
    canonical.setAttribute('href', window.location.origin + window.location.pathname);

    const jsonLd = ensureMeta('script[data-madplan-jsonld="1"]', () => {
      const script = document.createElement('script');
      script.setAttribute('type', 'application/ld+json');
      script.dataset.madplanJsonld = '1';
      return script;
    });
    jsonLd.textContent = JSON.stringify(
      {
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'MadPlan',
        url: window.location.origin,
        description,
        inLanguage: 'es',
        potentialAction: {
          '@type': 'SearchAction',
          target: `${window.location.origin}${window.location.pathname}?q={search_term_string}`,
          'query-input': 'required name=search_term_string',
        },
      },
      null,
      0,
    );
  }, [events, news]);

  return null;
}

