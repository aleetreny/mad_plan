# Auditoría Frontend MadPlan

## Diagnóstico inicial

- La app `frontend_new` tenía la lógica de negocio, filtros, estado de usuario y layout mezclados en un único componente principal.
- El build de producción no empaquetaba `outputs/`, así que el frontend era frágil fuera del entorno local de Vite.
- Había deuda de lint, errores potenciales de consistencia en fechas y una UX poco blindada para estados vacíos, agenda, share y navegación.
- `serve.py` y `tools/smoke_frontend.py` seguían apuntando al frontend legacy, lo que rompía la coherencia del repositorio.

## Arquitectura aplicada

```text
frontend_new/src
├─ app
│  ├─ App.tsx
│  ├─ providers/
│  └─ seo/
├─ domain
│  └─ madplan/
│     ├─ constants.ts
│     ├─ filters.ts
│     ├─ formatters.ts
│     ├─ normalizers.ts
│     └─ types.ts
├─ features
│  ├─ agenda/
│  ├─ discovery/
│  ├─ preferences/
│  └─ theme/
└─ shared
   ├─ hooks/
   ├─ lib/
   └─ ui/
```

## Principios usados

- `domain`: reglas puras de negocio para fechas, scoring, normalización y filtros.
- `features`: flujos de producto aislados por intención de usuario.
- `shared`: primitives reutilizables de UI y utilidades.
- `app`: composición global, providers y SEO.

## Mejoras ejecutadas

- Sincronización de filtros en URL.
- Agenda persistente con `localStorage`.
- Modal de evento con múltiples enlaces, sesiones y share real.
- Mapa lazy-loaded con límites válidos para Madrid.
- SEO base mejorado en `index.html` y SEO dinámico con JSON-LD.
- `vite.config.ts` ahora copia `outputs/` al build para que producción funcione.
- `serve.py` sirve el frontend actual compilado.
- `tools/smoke_frontend.py` valida la app real con Playwright.

## Riesgos aún existentes

- El payload `eventos_madrid_all.json` sigue siendo muy pesado para un producto de alto tráfico.
- El SEO será mejorable con SSR/SSG real o prerender de landing y categorías.
- El mapa sigue cargando muchos puntos; el siguiente salto debería ser clustering o tile-based aggregation.

## Siguiente iteración recomendada

1. Crear una capa BFF/API con feeds paginados y facetas precalculadas.
2. Prerenderizar portada y hubs de categorías para SEO competitivo.
3. Sustituir la carga del feed completo por búsqueda incremental y chunks por fecha/zona.
